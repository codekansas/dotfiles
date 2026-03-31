#!/usr/bin/env python3
"""Fetch and resolve GitHub pull request review threads via `gh api graphql`."""

import argparse
import json
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional, Union, cast


logger = logging.getLogger(__name__)

PR_URL_PATTERN = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)"
)

FETCH_QUERY = """\
query(
  $owner: String!,
  $repo: String!,
  $number: Int!,
  $commentsCursor: String,
  $reviewsCursor: String,
  $threadsCursor: String
) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number
      url
      title
      state
      comments(first: 100, after: $commentsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          body
          createdAt
          updatedAt
          author { login }
        }
      }
      reviews(first: 100, after: $reviewsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          state
          body
          submittedAt
          author { login }
        }
      }
      reviewThreads(first: 100, after: $threadsCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          diffSide
          startLine
          startDiffSide
          originalLine
          originalStartLine
          resolvedBy { login }
          comments(first: 100) {
            nodes {
              id
              body
              createdAt
              updatedAt
              author { login }
            }
          }
        }
      }
    }
  }
}
"""

RESOLVE_MUTATION = """\
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      id
      isResolved
    }
  }
}
"""


@dataclass(frozen=True)
class PullRequestRef:
    owner: str
    repo: str
    number: int

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def run_command(cmd: list[str], stdin: Optional[str] = None) -> str:
    result = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        joined = " ".join(cmd)
        raise RuntimeError(f"Command failed: {joined}\n{stderr}")
    return result.stdout


def run_json_command(
    cmd: list[str], stdin: Optional[str] = None
) -> dict[str, object]:
    raw_output = run_command(cmd, stdin=stdin)
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse JSON output:\n{raw_output}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Expected a JSON object from command output.")
    return cast(dict[str, object], payload)


def require_dict(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected {context} to be a JSON object.")
    return cast(dict[str, object], value)


def require_list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise RuntimeError(f"Expected {context} to be a JSON array.")
    return value


def require_str(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"Expected {context} to be a string.")
    return value


def require_int(value: object, context: str) -> int:
    if not isinstance(value, int):
        raise RuntimeError(f"Expected {context} to be an integer.")
    return value


def require_bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise RuntimeError(f"Expected {context} to be a boolean.")
    return value


def optional_str(value: object) -> Optional[str]:
    return value if isinstance(value, str) else None


def ensure_gh_authenticated() -> None:
    try:
        run_command(["gh", "auth", "status"])
    except RuntimeError as exc:
        raise RuntimeError(
            "gh auth status failed; run `gh auth login` before using this script."
        ) from exc


def parse_pr_url(pr_url: str) -> PullRequestRef:
    match = PR_URL_PATTERN.search(pr_url)
    if not match:
        raise RuntimeError(f"Could not parse pull request URL: {pr_url}")
    owner = match.group("owner")
    repo = match.group("repo")
    number = int(match.group("number"))
    return PullRequestRef(owner=owner, repo=repo, number=number)


def resolve_pr_ref(
    pr_selector: Optional[str], repo_slug: Optional[str]
) -> PullRequestRef:
    cmd = ["gh", "pr", "view"]
    if pr_selector:
        cmd.append(pr_selector)
    if repo_slug:
        cmd.extend(["--repo", repo_slug])
    cmd.extend(["--json", "url"])
    payload = run_json_command(cmd)
    pr_url = require_str(payload.get("url"), "pull request url")
    return parse_pr_url(pr_url)


def graphql_query(
    query: str,
    variables: dict[str, Union[str, int]],
) -> dict[str, object]:
    cmd = ["gh", "api", "graphql", "-F", "query=@-"]
    for key, value in variables.items():
        cmd.extend(["-F", f"{key}={value}"])
    payload = run_json_command(cmd, stdin=query)
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        raise RuntimeError(f"GitHub GraphQL errors:\n{json.dumps(errors, indent=2)}")
    return payload


def fetch_pull_request_data(
    pr_ref: PullRequestRef,
    include_resolved: bool,
) -> dict[str, object]:
    conversation_comments: list[dict[str, object]] = []
    reviews: list[dict[str, object]] = []
    review_threads: list[dict[str, object]] = []

    comments_cursor: Optional[str] = None
    reviews_cursor: Optional[str] = None
    threads_cursor: Optional[str] = None
    pr_meta: Optional[dict[str, object]] = None

    while True:
        variables: dict[str, Union[str, int]] = {
            "owner": pr_ref.owner,
            "repo": pr_ref.repo,
            "number": pr_ref.number,
        }
        if comments_cursor:
            variables["commentsCursor"] = comments_cursor
        if reviews_cursor:
            variables["reviewsCursor"] = reviews_cursor
        if threads_cursor:
            variables["threadsCursor"] = threads_cursor

        payload = graphql_query(FETCH_QUERY, variables)
        data = require_dict(payload.get("data"), "response.data")
        repository = require_dict(data.get("repository"), "response.data.repository")
        pull_request = require_dict(
            repository.get("pullRequest"), "response.data.repository.pullRequest"
        )

        if pr_meta is None:
            pr_meta = {
                "owner": pr_ref.owner,
                "repo": pr_ref.repo,
                "number": require_int(pull_request.get("number"), "pull request number"),
                "url": require_str(pull_request.get("url"), "pull request url"),
                "title": require_str(pull_request.get("title"), "pull request title"),
                "state": require_str(pull_request.get("state"), "pull request state"),
            }

        comments_connection = require_dict(
            pull_request.get("comments"), "pull request comments connection"
        )
        reviews_connection = require_dict(
            pull_request.get("reviews"), "pull request reviews connection"
        )
        threads_connection = require_dict(
            pull_request.get("reviewThreads"), "pull request reviewThreads connection"
        )

        conversation_comments.extend(
            [
                require_dict(comment, "conversation comment")
                for comment in require_list(
                    comments_connection.get("nodes"), "conversation comment nodes"
                )
            ]
        )
        reviews.extend(
            [
                require_dict(review, "review")
                for review in require_list(reviews_connection.get("nodes"), "review nodes")
            ]
        )
        review_threads.extend(
            [
                require_dict(thread, "review thread")
                for thread in require_list(threads_connection.get("nodes"), "review thread nodes")
            ]
        )

        comments_page_info = require_dict(
            comments_connection.get("pageInfo"), "conversation comments pageInfo"
        )
        reviews_page_info = require_dict(
            reviews_connection.get("pageInfo"), "reviews pageInfo"
        )
        threads_page_info = require_dict(
            threads_connection.get("pageInfo"), "review threads pageInfo"
        )

        comments_cursor = (
            require_str(comments_page_info.get("endCursor"), "comments endCursor")
            if require_bool(
                comments_page_info.get("hasNextPage"), "comments hasNextPage"
            )
            else None
        )
        reviews_cursor = (
            require_str(reviews_page_info.get("endCursor"), "reviews endCursor")
            if require_bool(reviews_page_info.get("hasNextPage"), "reviews hasNextPage")
            else None
        )
        threads_cursor = (
            require_str(threads_page_info.get("endCursor"), "threads endCursor")
            if require_bool(threads_page_info.get("hasNextPage"), "threads hasNextPage")
            else None
        )

        if not (comments_cursor or reviews_cursor or threads_cursor):
            break

    if pr_meta is None:
        raise RuntimeError("No pull request metadata was returned.")

    if not include_resolved:
        review_threads = [
            thread
            for thread in review_threads
            if not require_bool(thread.get("isResolved"), "review thread isResolved")
        ]

    return {
        "pull_request": pr_meta,
        "conversation_comments": conversation_comments,
        "reviews": reviews,
        "review_threads": review_threads,
    }


def resolve_review_threads(thread_ids: list[str]) -> list[dict[str, object]]:
    resolved_threads: list[dict[str, object]] = []
    for thread_id in thread_ids:
        payload = graphql_query(RESOLVE_MUTATION, {"threadId": thread_id})
        data = require_dict(payload.get("data"), "response.data")
        response = require_dict(
            data.get("resolveReviewThread"), "response.data.resolveReviewThread"
        )
        thread = require_dict(response.get("thread"), "resolved review thread")
        resolved_threads.append(
            {
                "id": require_str(thread.get("id"), "resolved review thread id"),
                "isResolved": require_bool(
                    thread.get("isResolved"), "resolved review thread isResolved"
                ),
            }
        )
    return resolved_threads


def short_body(body: Optional[str]) -> str:
    if not body:
        return ""
    first_line = body.strip().splitlines()[0].strip()
    return first_line[:117] + "..." if len(first_line) > 120 else first_line


def author_login_from_comment(comment: dict[str, object]) -> str:
    author = comment.get("author")
    if author is None:
        return "unknown"
    author_dict = require_dict(author, "comment author")
    login = author_dict.get("login")
    return optional_str(login) or "unknown"


def render_text_report(payload: dict[str, object]) -> str:
    pull_request = require_dict(payload.get("pull_request"), "pull request summary")
    review_threads = [
        require_dict(thread, "review thread")
        for thread in require_list(payload.get("review_threads"), "review threads")
    ]
    conversation_comments = require_list(
        payload.get("conversation_comments"), "conversation comments"
    )
    reviews = require_list(payload.get("reviews"), "reviews")

    lines = [
        (
            f"PR #{require_int(pull_request.get('number'), 'pull request number')}: "
            f"{require_str(pull_request.get('title'), 'pull request title')}"
        ),
        require_str(pull_request.get("url"), "pull request url"),
        (
            f"Unresolved threads: {len(review_threads)} | "
            f"Top-level comments: {len(conversation_comments)} | Reviews: {len(reviews)}"
        ),
        "",
    ]

    if not review_threads:
        lines.append("No unresolved review threads found.")
        return "\n".join(lines)

    for idx, thread in enumerate(review_threads, start=1):
        path = optional_str(thread.get("path")) or "<no path>"
        line_value = thread.get("line")
        line_suffix = f":{line_value}" if isinstance(line_value, int) else ""
        outdated = require_bool(thread.get("isOutdated"), "review thread isOutdated")
        status = "outdated" if outdated else "active"
        lines.append(f"{idx}. {path}{line_suffix} [{status}] id={require_str(thread.get('id'), 'thread id')}")

        comments = require_dict(thread.get("comments"), "thread comments connection")
        comment_nodes = [
            require_dict(comment, "thread comment")
            for comment in require_list(comments.get("nodes"), "thread comment nodes")
        ]
        for comment in comment_nodes:
            author_login = author_login_from_comment(comment)
            lines.append(
                f"   - {author_login}: {short_body(optional_str(comment.get('body')))}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and resolve GitHub pull request review threads.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch pull request comments, reviews, and review threads.",
    )
    fetch_parser.add_argument(
        "--pr",
        help="Pull request number, URL, or selector accepted by `gh pr view`.",
    )
    fetch_parser.add_argument(
        "--repo",
        help="Optional repository slug (`owner/repo`) passed to `gh pr view`.",
    )
    fetch_parser.add_argument(
        "--include-resolved",
        action="store_true",
        help="Include resolved review threads in the output.",
    )
    fetch_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text summary.",
    )

    resolve_parser = subparsers.add_parser(
        "resolve",
        help="Resolve one or more review thread ids.",
    )
    resolve_parser.add_argument(
        "thread_ids",
        nargs="+",
        help="One or more GraphQL review thread ids to resolve.",
    )
    resolve_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a text summary.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    ensure_gh_authenticated()

    if args.command == "fetch":
        pr_ref = resolve_pr_ref(args.pr, args.repo)
        logger.debug("Resolved pull request to %s#%s", pr_ref.slug, pr_ref.number)
        payload = fetch_pull_request_data(
            pr_ref=pr_ref,
            include_resolved=args.include_resolved,
        )
        if args.json:
            sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        else:
            sys.stdout.write(render_text_report(payload))
        return 0

    if args.command == "resolve":
        resolved_threads = resolve_review_threads(args.thread_ids)
        if args.json:
            sys.stdout.write(json.dumps({"resolved_threads": resolved_threads}, indent=2) + "\n")
        else:
            for thread in resolved_threads:
                sys.stdout.write(
                    f"Resolved {require_str(thread.get('id'), 'resolved thread id')}\n"
                )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
