"""Tests for the first-party dotfiles installer."""

import os
from pathlib import Path

import pytest

from dotfiles.config import ConfigError, resolve_profile
from dotfiles.console import Console, Level
from dotfiles.installer import Installer, InstallOptions


def quiet_console() -> Console:
    return Console(level=Level.ERROR, use_color=False)


def test_link_uses_dotfile_default_source(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    base = tmp_path / "repo"
    home.mkdir()
    base.mkdir()
    (base / "zshrc").write_text("# zshrc\n")
    monkeypatch.setenv("HOME", os.fspath(home))

    installer = Installer(base, quiet_console(), InstallOptions())

    assert installer.dispatch(
        [
            {"defaults": {"link": {"create": True, "relink": True}}},
            {"link": {"~/.zshrc": None}},
        ]
    )
    assert (home / ".zshrc").is_symlink()
    assert os.readlink(home / ".zshrc") == os.fspath(base / "zshrc")


def test_link_empty_source_points_to_repo_root(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    base = tmp_path / "repo"
    home.mkdir()
    base.mkdir()
    monkeypatch.setenv("HOME", os.fspath(home))

    installer = Installer(base, quiet_console(), InstallOptions())

    assert installer.dispatch(
        [
            {"defaults": {"link": {"create": True, "relink": True}}},
            {"link": {"~/.dotfiles": ""}},
        ]
    )
    assert (home / ".dotfiles").is_symlink()
    assert Path(home / ".dotfiles").resolve() == base.resolve()


def test_shell_runs_from_base_directory(tmp_path: Path) -> None:
    installer = Installer(tmp_path, quiet_console(), InstallOptions())

    assert installer.dispatch([{"shell": [["touch shell-created", "Creating file"]]}])
    assert (tmp_path / "shell-created").exists()


def test_profile_skip_directive(tmp_path: Path) -> None:
    installer = Installer(
        tmp_path,
        quiet_console(),
        InstallOptions(profile="devbox", profile_skip=frozenset({"shell"})),
    )

    assert installer.dispatch([{"shell": [["touch shell-created", "Creating file"]]}])
    assert not (tmp_path / "shell-created").exists()


def test_shell_command_profiles(tmp_path: Path) -> None:
    installer = Installer(tmp_path, quiet_console(), InstallOptions(profile="devbox"))

    assert installer.dispatch(
        [
            {
                "shell": [
                    {
                        "command": "touch local-only",
                        "description": "Local only",
                        "profiles": ["local"],
                    },
                    ["touch all-profiles", "All profiles"],
                ]
            }
        ]
    )
    assert not (tmp_path / "local-only").exists()
    assert (tmp_path / "all-profiles").exists()


def test_resolve_profile_skip() -> None:
    profile = resolve_profile(
        [
            {
                "profiles": {
                    "local": {},
                    "devbox": {"skip": ["crontab"]},
                }
            }
        ],
        "devbox",
    )

    assert profile.name == "devbox"
    assert profile.skip == frozenset({"crontab"})


def test_resolve_profile_rejects_unknown_profile() -> None:
    with pytest.raises(ConfigError):
        resolve_profile([{"profiles": {"local": {}}}], "devbox")
