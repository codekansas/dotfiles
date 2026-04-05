#!/usr/bin/env python3
"""Manage a repo-local `.wiki/` knowledge base."""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import sys
from typing import Optional


TYPE_ORDER = {
    "overview": 0,
    "source": 1,
    "entity": 2,
    "concept": 3,
    "analysis": 4,
    "question": 5,
    "note": 6,
}

TYPE_LABELS = {
    "overview": "Overview",
    "source": "Sources",
    "entity": "Entities",
    "concept": "Concepts",
    "analysis": "Analyses",
    "question": "Questions",
    "note": "Notes",
    "other": "Other",
}

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


@dataclass(frozen=True)
class WikiPaths:
    repo_root: Path
    git_dir: Path
    skill_dir: Path
    wiki_dir: Path
    pages_dir: Path
    raw_dir: Path
    index_path: Path
    log_path: Path
    overview_path: Path
    gitignore_path: Path


@dataclass(frozen=True)
class PageRecord:
    absolute_path: Path
    relative_path: Path
    title: str
    page_type: str
    summary: str
    updated_at: str
    source_count: str
    metadata: dict[str, str]
    body: str


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def run_git(args: list[str], cwd: Optional[Path] = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=True,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def discover_paths() -> WikiPaths:
    try:
        repo_root = Path(run_git(["rev-parse", "--show-toplevel"])).resolve()
        git_dir_output = Path(run_git(["rev-parse", "--git-dir"], cwd=repo_root))
    except subprocess.CalledProcessError as exc:
        print("wiki: run this inside a git repository", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc

    git_dir = git_dir_output if git_dir_output.is_absolute() else (repo_root / git_dir_output)
    skill_dir = Path(__file__).resolve().parent.parent
    wiki_dir = repo_root / ".wiki"
    pages_dir = wiki_dir / "pages"
    raw_dir = wiki_dir / "raw"
    return WikiPaths(
        repo_root=repo_root,
        git_dir=git_dir.resolve(),
        skill_dir=skill_dir,
        wiki_dir=wiki_dir,
        pages_dir=pages_dir,
        raw_dir=raw_dir,
        index_path=wiki_dir / "index.md",
        log_path=wiki_dir / "log.md",
        overview_path=pages_dir / "overview.md",
        gitignore_path=wiki_dir / ".gitignore",
    )


def ensure_git_exclude(paths: WikiPaths) -> None:
    exclude_path = paths.git_dir / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    exclude_path.touch(exist_ok=True)

    needle = "/.wiki/"
    current_text = exclude_path.read_text(encoding="utf-8")
    if needle not in current_text.splitlines():
        with exclude_path.open("a", encoding="utf-8") as handle:
            if current_text and not current_text.endswith("\n"):
                handle.write("\n")
            handle.write(f"{needle}\n")


def ensure_layout(paths: WikiPaths) -> list[Path]:
    created_paths: list[Path] = []

    for directory in (
        paths.wiki_dir,
        paths.pages_dir,
        paths.pages_dir / "sources",
        paths.pages_dir / "entities",
        paths.pages_dir / "concepts",
        paths.pages_dir / "analyses",
        paths.raw_dir,
        paths.raw_dir / "assets",
    ):
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created_paths.append(directory)

    if not paths.gitignore_path.exists():
        gitignore_template = (
            paths.skill_dir / "assets" / "repo-local" / ".gitignore"
        ).read_text(encoding="utf-8")
        paths.gitignore_path.write_text(gitignore_template, encoding="utf-8")
        created_paths.append(paths.gitignore_path)

    ensure_git_exclude(paths)

    if not paths.overview_path.exists():
        overview_text = f"""---
title: Overview
type: overview
summary: High-level synthesis of the knowledge compiled in this wiki.
updated_at: {now_utc()}
source_count: 0
---

# Overview

## Current Synthesis

## Key Entities

## Key Concepts

## Open Questions

## Source Map
"""
        paths.overview_path.write_text(overview_text, encoding="utf-8")
        created_paths.append(paths.overview_path)

    if not paths.log_path.exists():
        paths.log_path.write_text(
            "# Wiki Log\n\nAppend-only timeline of wiki activity.\n",
            encoding="utf-8",
        )
        created_paths.append(paths.log_path)

    return created_paths


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    metadata: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        metadata[key.strip()] = value.strip()

    body = text[match.end() :]
    return metadata, body


def first_heading(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def first_summary_line(body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        return stripped
    return ""


def infer_type(page_path: Path, paths: WikiPaths) -> str:
    if page_path == paths.overview_path:
        return "overview"

    try:
        relative_parent = page_path.relative_to(paths.pages_dir).parent
    except ValueError:
        return "other"

    if relative_parent == Path("."):
        return "note"

    parent_name = relative_parent.parts[0]
    if parent_name.endswith("ies"):
        return parent_name[:-3] + "y"
    if parent_name.endswith("s"):
        return parent_name[:-1]
    return parent_name


def relative_to_wiki(paths: WikiPaths, page_path: Path) -> Path:
    return page_path.relative_to(paths.wiki_dir)


def collect_page_records(paths: WikiPaths) -> list[PageRecord]:
    records: list[PageRecord] = []
    for page_path in sorted(paths.pages_dir.rglob("*.md")):
        text = page_path.read_text(encoding="utf-8")
        metadata, body = split_frontmatter(text)
        title = (
            metadata.get("title")
            or first_heading(body)
            or page_path.stem.replace("-", " ").title()
        )
        page_type = metadata.get("type") or infer_type(page_path, paths)
        summary = metadata.get("summary") or first_summary_line(body) or "No summary yet."
        updated_at = metadata.get("updated_at") or now_utc()
        source_count = metadata.get("source_count", "")
        records.append(
            PageRecord(
                absolute_path=page_path,
                relative_path=relative_to_wiki(paths, page_path),
                title=title,
                page_type=page_type,
                summary=summary,
                updated_at=updated_at,
                source_count=source_count,
                metadata=metadata,
                body=body,
            )
        )
    return records


def type_order(page_type: str) -> int:
    return TYPE_ORDER.get(page_type, 99)


def type_label(page_type: str) -> str:
    return TYPE_LABELS.get(page_type, page_type.replace("-", " ").title())


def rebuild_index(paths: WikiPaths) -> list[PageRecord]:
    ensure_layout(paths)
    records = sorted(
        collect_page_records(paths),
        key=lambda record: (
            type_order(record.page_type),
            record.title.casefold(),
            str(record.relative_path),
        ),
    )

    lines = [
        "# Wiki Index",
        "",
        "This index is rebuilt from page frontmatter by `codex/skills/wiki/scripts/wiki.sh reindex`.",
        f"Last rebuilt: {now_utc()}",
        "",
    ]

    current_type = ""
    for record in records:
        if record.page_type != current_type:
            if current_type:
                lines.append("")
            current_type = record.page_type
            lines.extend([f"## {type_label(current_type)}", ""])

        suffix = f" (updated {record.updated_at[:10]})"
        if record.source_count:
            suffix += f" [sources: {record.source_count}]"

        lines.append(
            f"- [{record.title}]({record.relative_path.as_posix()}) - {record.summary}{suffix}"
        )

    lines.append("")
    paths.index_path.write_text("\n".join(lines), encoding="utf-8")
    return records


def parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def markdown_links(items: list[str]) -> str:
    links: list[str] = []
    for item in items:
        label = Path(item).name or item
        links.append(f"[{label}]({item})")
    return ", ".join(links)


def append_log_entry(
    paths: WikiPaths,
    *,
    kind: str,
    title: str,
    summary: str,
    pages: list[str],
    sources: list[str],
) -> None:
    ensure_layout(paths)

    lines = [
        "",
        f"## [{today_utc()}] {kind} | {title}",
        f"- timestamp: {now_utc()}",
    ]
    if summary:
        lines.append(f"- summary: {summary}")
    if pages:
        lines.append(f"- pages: {markdown_links(pages)}")
    if sources:
        lines.append(f"- sources: {markdown_links(sources)}")

    with paths.log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
        handle.write("\n")


def resolve_relative_link(source_path: Path, raw_target: str) -> Optional[Path]:
    if "://" in raw_target or raw_target.startswith("mailto:"):
        return None

    target = raw_target.split("#", 1)[0].strip()
    if not target or not target.endswith(".md"):
        return None

    return (source_path.parent / target).resolve()


def lint_pages(paths: WikiPaths) -> list[str]:
    ensure_layout(paths)
    records = collect_page_records(paths)
    known_pages = {record.absolute_path.resolve() for record in records}
    inbound_links: dict[Path, int] = defaultdict(int)
    issues: list[str] = []

    for record in records:
        for field_name in ("title", "type", "summary", "updated_at"):
            if field_name not in record.metadata or not record.metadata[field_name]:
                issues.append(
                    f"missing-meta\t{record.relative_path.as_posix()}\t{field_name}"
                )

        for raw_target in MARKDOWN_LINK_RE.findall(record.body):
            resolved_target = resolve_relative_link(record.absolute_path, raw_target)
            if resolved_target is None:
                continue

            if resolved_target not in known_pages:
                issues.append(
                    f"broken-link\t{record.relative_path.as_posix()}\t{raw_target}"
                )
                continue

            inbound_links[resolved_target] += 1

    for record in records:
        if record.page_type == "overview":
            continue
        if inbound_links.get(record.absolute_path.resolve(), 0) == 0:
            issues.append(f"orphan-page\t{record.relative_path.as_posix()}")

    return issues


def handle_init(_: argparse.Namespace) -> int:
    paths = discover_paths()
    created_paths = ensure_layout(paths)
    rebuild_index(paths)

    if created_paths:
        pages_for_log = ["pages/overview.md", "index.md"]
        append_log_entry(
            paths,
            kind="init",
            title="wiki initialized",
            summary="Created the repo-local wiki layout and starter overview page.",
            pages=pages_for_log,
            sources=[],
        )

    print(paths.wiki_dir)
    return 0


def handle_reindex(_: argparse.Namespace) -> int:
    paths = discover_paths()
    records = rebuild_index(paths)
    print(f"reindexed {len(records)} pages under {paths.wiki_dir}")
    return 0


def handle_log(args: argparse.Namespace) -> int:
    paths = discover_paths()
    append_log_entry(
        paths,
        kind=args.kind,
        title=args.title,
        summary=args.summary or "",
        pages=parse_csv(args.pages or ""),
        sources=parse_csv(args.sources or ""),
    )
    print(paths.log_path)
    return 0


def handle_lint(_: argparse.Namespace) -> int:
    paths = discover_paths()
    issues = lint_pages(paths)
    if not issues:
        print("wiki lint: clean")
        return 0

    print("wiki lint: issues found")
    for issue in issues:
        print(issue)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a repo-local .wiki/")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create the .wiki layout")
    init_parser.set_defaults(handler=handle_init)

    reindex_parser = subparsers.add_parser("reindex", help="Rebuild .wiki/index.md")
    reindex_parser.set_defaults(handler=handle_reindex)

    log_parser = subparsers.add_parser("log", help="Append an entry to .wiki/log.md")
    log_parser.add_argument(
        "--kind",
        required=True,
        help="Event kind such as ingest, query, or lint",
    )
    log_parser.add_argument("--title", required=True, help="Short title for the log entry")
    log_parser.add_argument("--summary", help="One-line summary")
    log_parser.add_argument("--pages", help="Comma-separated .wiki-relative page paths")
    log_parser.add_argument("--sources", help="Comma-separated .wiki-relative source paths")
    log_parser.set_defaults(handler=handle_log)

    lint_parser = subparsers.add_parser("lint", help="Run structural wiki health checks")
    lint_parser.set_defaults(handler=handle_lint)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
