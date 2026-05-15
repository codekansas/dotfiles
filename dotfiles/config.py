"""YAML config loading for the dotfiles installer."""

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

ConfigTask = dict[str, object]
DEFAULT_PROFILE = "local"


class ConfigError(Exception):
    """Raised when the installer config is missing or malformed."""


@dataclass(frozen=True)
class ProfileConfig:
    """Install profile settings resolved from the config file."""

    name: str
    skip: frozenset[str] = frozenset()


def read_config(config_file: Path) -> list[ConfigTask]:
    """Read an install config file.

    Args:
        config_file: Path to the YAML config file.

    Returns:
        Ordered config tasks from the YAML file.

    Raises:
        ConfigError: If the config file does not contain a list of mappings.
    """
    data = yaml.safe_load(config_file.read_text())
    if data is None:
        return []
    if not isinstance(data, list):
        raise ConfigError("Configuration file must be a list of tasks")

    tasks: list[ConfigTask] = []
    for task_idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ConfigError(f"Task {task_idx} must be a mapping")
        if not all(isinstance(key, str) for key in item):
            raise ConfigError(f"Task {task_idx} contains a non-string directive")
        tasks.append(cast(ConfigTask, item))
    return tasks


def resolve_profile(tasks: list[ConfigTask], profile_name: str) -> ProfileConfig:
    """Resolve profile settings from install config tasks.

    Args:
        tasks: Ordered config tasks from the YAML file.
        profile_name: Requested profile name.

    Returns:
        Resolved profile settings.

    Raises:
        ConfigError: If profile configuration is malformed or unknown.
    """
    profiles = _find_profiles(tasks)
    if profiles is None:
        if profile_name == DEFAULT_PROFILE:
            return ProfileConfig(name=profile_name)
        raise ConfigError(f"Unknown profile {profile_name!r}; no profiles are configured")

    if profile_name not in profiles:
        available = ", ".join(sorted(profiles))
        raise ConfigError(f"Unknown profile {profile_name!r}; available profiles: {available}")

    profile_data = profiles[profile_name]
    if profile_data is None:
        settings: dict[str, object] = {}
    else:
        settings = _as_mapping(profile_data, f"profile {profile_name!r}")
    return ProfileConfig(
        name=profile_name,
        skip=frozenset(_as_string_list(settings.get("skip", []), f"profile {profile_name!r} skip")),
    )


def _find_profiles(tasks: list[ConfigTask]) -> dict[str, object] | None:
    for task in tasks:
        if "profiles" in task:
            return _as_mapping(task["profiles"], "profiles")
    return None


def _as_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise ConfigError(f"{label} contains a non-string key")
    return cast(dict[str, object], value)


def _as_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ConfigError(f"{label} must be a list")
    if not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{label} must contain only strings")
    return cast(list[str], value)
