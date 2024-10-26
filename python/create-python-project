#!/usr/bin/env python
"""Creates a new project, copying a standard format."""

import argparse
import re
from pathlib import Path


def get_default_author() -> str:
    try:
        import git

        return git.config.GitConfigParser().get_value("user", "name")  # type: ignore[return-value]
    except Exception:
        raise ValueError("Could not get configured Git author; please manually specify the --author argument")


def get_default_email() -> str:
    try:
        import git

        return git.config.GitConfigParser().get_value("user", "email")  # type: ignore[return-value]
    except Exception:
        raise ValueError("Could not get configured Git email; please manually specify the --email argument")


def cleanup_url(s: str) -> str:
    s = s.replace(":", "/")
    s = s.replace("git@", "https://")
    s = s.replace(".git", "")
    return s


def get_default_url() -> str:
    try:
        import git

        repo = git.Repo(search_parent_directories=True)
        return cleanup_url(repo.remote().url)
    except Exception:
        raise ValueError("Could not get configured Git URL; please manually specify the --url argument")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", help="Project name")
    parser.add_argument("--description", help="Project description; if not provided, uses a generic default")
    parser.add_argument("--author", help="Project author; if not provided, defaults to the current user")
    parser.add_argument("--email", help="Project email; if not provided, defaults to <author>@users.noreply.github.com")
    parser.add_argument("--url", help="Project URL; if not provided, defaults to https://github.com/<author>/<name>")
    parser.add_argument("--version", help="Python; if not provided, defaults to 3.11", default="3.11")
    parser.add_argument("--python-name", help="Python package name", default=None)
    args = parser.parse_args()

    # Gets default values for the project metadata.
    name: str = args.name
    description: str = args.description or f"The {name} project"
    author: str = args.author or get_default_author()
    email: str = args.email or get_default_email()
    url: str = args.url or get_default_url()
    version: str = args.version

    # Checks that the name is a valid Python package name.
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", name):
        raise ValueError(f"Invalid project name: {name}")

    # Replaces hyphens with underscores in the project name.
    python_safe_name = args.python_name or name.replace("-", "_")
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", python_safe_name):
        raise ValueError(f"Invalid Python package name: {python_safe_name}")

    replacements = {
        "[[PROJECT NAME]]": name,
        "[[PROJECT PYTHON NAME]]": python_safe_name,
        "[[PROJECT DESCRIPTION]]": description,
        "[[PROJECT AUTHOR]]": author,
        "[[PROJECT EMAIL]]": email,
        "[[PROJECT URL]]": url,
        "[[PROJECT PYTHON VERSION]]": version,
    }

    # Copies the `template` directory to the target directory, replacing placeholders.
    src_dir = (Path(__file__).resolve().parent / "template").resolve()
    tgt_dir = (Path.cwd() / python_safe_name).resolve()
    tgt_dir.mkdir(parents=True, exist_ok=True)

    def recursive_copy(src: Path, tgt: Path) -> None:
        if src.is_dir():
            if src.name in ("__pycache__", ".git", ".ruff_cache", ".pytest_cache"):
                return
            tgt.mkdir(parents=True, exist_ok=True)
            for src_file in src.iterdir():
                recursive_copy(src_file, tgt / src_file.name)
        else:
            with src.open("r", encoding="utf-8") as f:
                src_contents = f.read()
            tgt_contents = src_contents
            for src_str, tgt_str in replacements.items():
                tgt_contents = tgt_contents.replace(src_str, tgt_str)
            with tgt.open("w", encoding="utf-8") as f:
                f.write(tgt_contents)

    recursive_copy(src_dir, tgt_dir)

    # Renames the `project` subdirectory to the project name.
    (tgt_dir / "project").rename(tgt_dir / python_safe_name)


if __name__ == "__main__":
    main()
