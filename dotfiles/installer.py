"""Dotfiles installation engine."""

import glob
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from dotfiles.config import ConfigTask
from dotfiles.console import Console


class InstallError(Exception):
    """Raised when installation cannot continue."""


@dataclass(frozen=True)
class InstallOptions:
    """Runtime options that affect directive dispatch."""

    only: set[str] | None = None
    skip: set[str] | None = None
    profile: str = "local"
    profile_skip: frozenset[str] = frozenset()
    exit_on_failure: bool = False
    verbose: int = 0


class Installer:
    """Install dotfiles from an `install.conf.yaml`-style config."""

    def __init__(self, base_directory: Path, console: Console, options: InstallOptions) -> None:
        path = base_directory.expanduser().resolve()
        if not path.exists():
            raise InstallError("Nonexistent base directory")
        self._base_directory = path
        self._console = console
        self._options = options
        self._defaults: dict[str, object] = {}

    def dispatch(self, tasks: list[ConfigTask]) -> bool:
        success = True
        for task in tasks:
            for action, data in task.items():
                if action == "profiles":
                    continue

                skip_message = self._skip_message(action)
                if skip_message is not None and action != "defaults":
                    self._console.info(skip_message)
                    continue

                handled = False
                if action == "defaults":
                    self._defaults = self._as_mapping(data, "defaults")
                    handled = True
                elif action == "clean":
                    success = self._record_success(success, self._handle_clean(data), action)
                    handled = True
                elif action == "create":
                    success = self._record_success(success, self._handle_create(data), action)
                    handled = True
                elif action == "link":
                    success = self._record_success(success, self._handle_link(data), action)
                    handled = True
                elif action == "shell":
                    success = self._record_success(success, self._handle_shell(data), action)
                    handled = True
                elif action == "crontab":
                    success = self._record_success(success, self._handle_crontab(data), action)
                    handled = True

                if not handled:
                    success = False
                    self._console.error(f"Action {action} not handled")
                    if self._options.exit_on_failure:
                        return False
        return success

    def _record_success(self, previous: bool, local_success: bool, action: str) -> bool:
        if not local_success and self._options.exit_on_failure:
            self._console.error(f"Action {action} failed")
            raise InstallError(f"Action {action} failed")
        return previous and local_success

    def _skip_message(self, action: str) -> str | None:
        if action in self._options.profile_skip:
            return f"Skipping action {action} for profile {self._options.profile}"
        if self._options.only is not None and action not in self._options.only:
            return f"Skipping action {action}"
        if self._options.skip is not None and action in self._options.skip:
            return f"Skipping action {action}"
        return None

    def _base(self, *, canonical_path: bool = True) -> str:
        if canonical_path:
            return os.path.realpath(self._base_directory)
        return os.fspath(self._base_directory)

    def _directive_defaults(self, directive: str) -> dict[str, object]:
        value = self._defaults.get(directive, {})
        if isinstance(value, dict):
            return cast(dict[str, object], value.copy())
        return {}

    def _handle_clean(self, data: object) -> bool:
        success = True
        defaults = self._directive_defaults("clean")
        for target, options in self._iter_path_options(data, "clean"):
            force = bool(defaults.get("force", False))
            recursive = bool(defaults.get("recursive", False))
            if options:
                force = bool(options.get("force", force))
                recursive = bool(options.get("recursive", recursive))
            success = self._clean(target, force, recursive) and success
        if success:
            self._console.info("All targets have been cleaned")
        else:
            self._console.error("Some targets were not successfully cleaned")
        return success

    def _clean(self, target: str, force: bool, recursive: bool) -> bool:
        target_path = os.path.expandvars(os.path.expanduser(target))
        if not os.path.isdir(target_path):
            self._console.debug(f"Ignoring nonexistent directory {target}")
            return True

        for item in os.listdir(target_path):
            path = os.path.abspath(os.path.join(target_path, item))
            if recursive and os.path.isdir(path):
                self._clean(path, force, recursive)
            if not os.path.exists(path) and os.path.islink(path):
                points_at = os.path.join(os.path.dirname(path), os.readlink(path))
                if sys.platform[:5] == "win32" and points_at.startswith("\\\\?\\"):
                    points_at = points_at[4:]
                if self._in_directory(path, self._base()) or force:
                    self._console.lowinfo(f"Removing invalid link {path} -> {points_at}")
                    os.remove(path)
                else:
                    self._console.lowinfo(f"Link {path} -> {points_at} not removed.")
        return True

    def _in_directory(self, path: str, directory: str) -> bool:
        real_directory = os.path.join(os.path.realpath(directory), "")
        real_path = os.path.realpath(path)
        return os.path.commonprefix([real_path, real_directory]) == real_directory

    def _handle_create(self, data: object) -> bool:
        success = True
        defaults = self._directive_defaults("create")
        for path, options in self._iter_path_options(data, "create"):
            mode = self._as_mode(defaults.get("mode", 0o777), "create mode")
            if options:
                mode = self._as_mode(options.get("mode", mode), "create mode")
            success = self._create_path(path, mode) and success
        if success:
            self._console.info("All paths have been set up")
        else:
            self._console.error("Some paths were not successfully set up")
        return success

    def _create_path(self, path: str, mode: int) -> bool:
        full_path = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
        if os.path.exists(full_path):
            self._console.lowinfo(f"Path exists {full_path}")
            return True
        self._console.debug(f"Trying to create path {full_path} with mode {mode:o}")
        try:
            self._console.lowinfo(f"Creating path {full_path}")
            os.makedirs(full_path, mode)
            os.chmod(full_path, mode)
        except OSError:
            self._console.warning(f"Failed to create path {full_path}")
            return False
        return True

    def _handle_link(self, data: object) -> bool:
        success = True
        links = self._as_mapping(data, "link")
        defaults = self._directive_defaults("link")
        for destination_obj, source in links.items():
            destination = os.path.expandvars(str(destination_obj))
            relative = bool(defaults.get("relative", False))
            canonical_path = bool(defaults.get("canonicalize", defaults.get("canonicalize-path", True)))
            force = bool(defaults.get("force", False))
            relink = bool(defaults.get("relink", False))
            create = bool(defaults.get("create", False))
            use_glob = bool(defaults.get("glob", False))
            base_prefix = str(defaults.get("prefix", ""))
            test = defaults.get("if")
            ignore_missing = bool(defaults.get("ignore-missing", False))
            exclude_paths = self._as_string_list(defaults.get("exclude", []), "link exclude")

            if isinstance(source, dict):
                source_options = cast(dict[str, object], source)
                test = source_options.get("if", test)
                relative = bool(source_options.get("relative", relative))
                canonical_path = bool(
                    source_options.get("canonicalize", source_options.get("canonicalize-path", canonical_path))
                )
                force = bool(source_options.get("force", force))
                relink = bool(source_options.get("relink", relink))
                create = bool(source_options.get("create", create))
                use_glob = bool(source_options.get("glob", use_glob))
                base_prefix = str(source_options.get("prefix", base_prefix))
                ignore_missing = bool(source_options.get("ignore-missing", ignore_missing))
                exclude_paths = self._as_string_list(source_options.get("exclude", exclude_paths), "link exclude")
                path = self._default_source(destination, source_options.get("path"))
            else:
                path = self._default_source(destination, source)

            if test is not None and not self._test_success(str(test)):
                self._console.lowinfo(f"Skipping {destination}")
                continue

            path = os.path.normpath(os.path.expandvars(os.path.expanduser(path)))
            if use_glob and self._has_glob_chars(path):
                success = self._link_glob(
                    destination,
                    path,
                    exclude_paths,
                    base_prefix,
                    create,
                    force,
                    relink,
                    relative,
                    canonical_path,
                    ignore_missing,
                ) and success
                continue

            if create:
                success = self._create_link_parent(destination) and success
            if not ignore_missing and not self._exists(os.path.join(self._base(), path)):
                success = False
                self._console.warning(f"Nonexistent source {destination} -> {path}")
                continue
            if force or relink:
                success = self._delete_link(path, destination, relative, canonical_path, force) and success
            success = self._link(path, destination, relative, canonical_path, ignore_missing) and success

        if success:
            self._console.info("All links have been set up")
        else:
            self._console.error("Some links were not successfully set up")
        return success

    def _link_glob(
        self,
        destination: str,
        path: str,
        exclude_paths: list[str],
        base_prefix: str,
        create: bool,
        force: bool,
        relink: bool,
        relative: bool,
        canonical_path: bool,
        ignore_missing: bool,
    ) -> bool:
        success = True
        glob_results = self._create_glob_results(path, exclude_paths)
        self._console.lowinfo(f"Globs from '{path}': {glob_results}")
        for glob_full_item in glob_results:
            glob_dirname = os.path.dirname(os.path.commonprefix([path, glob_full_item]))
            if len(glob_dirname) == 0:
                glob_item = glob_full_item
            else:
                glob_item = glob_full_item[len(glob_dirname) + 1 :]
            if base_prefix:
                glob_item = base_prefix + glob_item
            glob_link_destination = os.path.join(destination, glob_item)
            if create:
                success = self._create_link_parent(glob_link_destination) and success
            if force or relink:
                success = self._delete_link(
                    glob_full_item,
                    glob_link_destination,
                    relative,
                    canonical_path,
                    force,
                ) and success
            success = self._link(
                glob_full_item,
                glob_link_destination,
                relative,
                canonical_path,
                ignore_missing,
            ) and success
        return success

    def _test_success(self, command: str) -> bool:
        ret = self._shell_command(command, cwd=self._base())
        if ret != 0:
            self._console.debug(f"Test '{command}' returned false")
        return ret == 0

    def _default_source(self, destination: str, source: object) -> str:
        if source is None:
            basename = os.path.basename(destination)
            if basename.startswith("."):
                return basename[1:]
            return basename
        return str(source)

    def _has_glob_chars(self, path: str) -> bool:
        return any(char in path for char in "?*[")

    def _glob(self, path: str) -> list[str]:
        found = glob.glob(path, recursive=True)
        normalized = [os.path.normpath(item) for item in found]
        if "**" in path and not path.endswith(str(os.sep)):
            self._console.debug(f"Excluding directories from recursive glob: {path}")
            normalized = [item for item in normalized if os.path.isfile(item)]
        return normalized

    def _create_glob_results(self, path: str, exclude_paths: list[str]) -> list[str]:
        self._console.debug(f"Globbing with pattern: {path}")
        include = self._glob(path)
        self._console.debug(f"Glob found : {include}")
        exclude: list[str] = []
        for exclude_path in exclude_paths:
            self._console.debug(f"Excluding globs with pattern: {exclude_path}")
            exclude.extend(self._glob(exclude_path))
        self._console.debug(f"Excluded globs from '{path}': {exclude}")
        return list(set(include) - set(exclude))

    def _is_link(self, path: str) -> bool:
        return os.path.islink(os.path.expanduser(path))

    def _link_destination(self, path: str) -> str:
        target = os.readlink(os.path.expanduser(path))
        if sys.platform[:5] == "win32" and target.startswith("\\\\?\\"):
            target = target[4:]
        return target

    def _exists(self, path: str) -> bool:
        return os.path.exists(os.path.expanduser(path))

    def _create_link_parent(self, path: str) -> bool:
        parent = os.path.abspath(os.path.join(os.path.expanduser(path), os.pardir))
        if self._exists(parent):
            return True
        self._console.debug(f"Try to create parent: {parent}")
        try:
            os.makedirs(parent)
        except OSError:
            self._console.warning(f"Failed to create directory {parent}")
            return False
        self._console.lowinfo(f"Creating directory {parent}")
        return True

    def _delete_link(
        self,
        source: str,
        path: str,
        relative: bool,
        canonical_path: bool,
        force: bool,
    ) -> bool:
        source_path = os.path.join(self._base(canonical_path=canonical_path), source)
        full_path = os.path.abspath(os.path.expanduser(path))
        if relative:
            source_path = self._relative_path(source_path, full_path)
        if (self._is_link(path) and self._link_destination(path) != source_path) or (
            self._exists(path) and not self._is_link(path)
        ):
            removed = False
            try:
                if os.path.islink(full_path):
                    os.unlink(full_path)
                    removed = True
                elif force:
                    if os.path.isdir(full_path):
                        shutil.rmtree(full_path)
                    else:
                        os.remove(full_path)
                    removed = True
            except OSError:
                self._console.warning(f"Failed to remove {path}")
                return False
            if removed:
                self._console.lowinfo(f"Removing {path}")
        return True

    def _relative_path(self, source: str, destination: str) -> str:
        return os.path.relpath(source, os.path.dirname(destination))

    def _link(
        self,
        source: str,
        link_name: str,
        relative: bool,
        canonical_path: bool,
        ignore_missing: bool,
    ) -> bool:
        success = False
        destination = os.path.abspath(os.path.expanduser(link_name))
        base_directory = self._base(canonical_path=canonical_path)
        absolute_source = os.path.join(base_directory, source)
        normalized_link_name = os.path.normpath(link_name)
        if relative:
            source_path = self._relative_path(absolute_source, destination)
        else:
            source_path = absolute_source

        if (
            not self._exists(normalized_link_name)
            and self._is_link(normalized_link_name)
            and self._link_destination(normalized_link_name) != source_path
        ):
            target = self._link_destination(normalized_link_name)
            self._console.warning(f"Invalid link {normalized_link_name} -> {target}")
        elif not self._exists(normalized_link_name) and (ignore_missing or self._exists(absolute_source)):
            try:
                os.symlink(source_path, destination)
            except OSError:
                self._console.warning(f"Linking failed {normalized_link_name} -> {source_path}")
            else:
                self._console.lowinfo(f"Creating link {normalized_link_name} -> {source_path}")
                success = True
        elif self._exists(normalized_link_name) and not self._is_link(normalized_link_name):
            self._console.warning(f"{normalized_link_name} already exists but is a regular file or directory")
        elif self._is_link(normalized_link_name) and self._link_destination(normalized_link_name) != source_path:
            target = self._link_destination(normalized_link_name)
            self._console.warning(f"Incorrect link {normalized_link_name} -> {target}")
        elif not self._exists(absolute_source):
            if self._is_link(normalized_link_name):
                self._console.warning(f"Nonexistent source {normalized_link_name} -> {source_path}")
            else:
                self._console.warning(f"Nonexistent source for {normalized_link_name} : {source_path}")
        else:
            self._console.lowinfo(f"Link exists {normalized_link_name} -> {source_path}")
            success = True
        return success

    def _handle_shell(self, data: object) -> bool:
        success = True
        defaults = self._directive_defaults("shell")
        for item in self._as_list(data, "shell"):
            stdin = bool(defaults.get("stdin", False))
            stdout = bool(defaults.get("stdout", False))
            stderr = bool(defaults.get("stderr", False))
            quiet = bool(defaults.get("quiet", False))

            if isinstance(item, dict):
                command_data = cast(dict[str, object], item)
                command = str(command_data["command"])
                message_obj = command_data.get("description")
                message = None if message_obj is None else str(message_obj)
                if not self._profile_allows(command_data, "shell command"):
                    self._console.lowinfo(f"Skipping {message or command} for profile {self._options.profile}")
                    continue
                stdin = bool(command_data.get("stdin", stdin))
                stdout = bool(command_data.get("stdout", stdout))
                stderr = bool(command_data.get("stderr", stderr))
                quiet = bool(command_data.get("quiet", quiet))
            elif isinstance(item, list):
                if not item:
                    self._console.warning("Skipping empty shell command")
                    success = False
                    continue
                command = str(item[0])
                message = str(item[1]) if len(item) > 1 else None
            else:
                command = str(item)
                message = None

            if quiet:
                if message is not None:
                    self._console.lowinfo(message)
            elif message is None:
                self._console.lowinfo(command)
            else:
                self._console.lowinfo(f"{message} [{command}]")

            if self._options.verbose > 1:
                stdout = True
                stderr = True
            ret = self._shell_command(
                command,
                cwd=self._base(),
                enable_stdin=stdin,
                enable_stdout=stdout,
                enable_stderr=stderr,
            )
            if ret != 0:
                success = False
                self._console.warning(f"Command [{command}] failed")

        if success:
            self._console.info("All commands have been executed")
        else:
            self._console.error("Some commands were not successfully executed")
        return success

    def _profile_allows(self, options: dict[str, object], label: str) -> bool:
        profiles_obj = options.get("profiles")
        if profiles_obj is not None:
            profiles = self._as_string_list(profiles_obj, f"{label} profiles")
            if self._options.profile not in profiles:
                return False

        skip_profiles_obj = options.get("skip_profiles")
        if skip_profiles_obj is not None:
            skip_profiles = self._as_string_list(skip_profiles_obj, f"{label} skip_profiles")
            if self._options.profile in skip_profiles:
                return False

        return True

    def _shell_command(
        self,
        command: str,
        *,
        cwd: str,
        enable_stdin: bool = False,
        enable_stdout: bool = False,
        enable_stderr: bool = False,
    ) -> int:
        with open(os.devnull) as devnull_r, open(os.devnull, "w") as devnull_w:
            stdin = None if enable_stdin else devnull_r
            stdout = None if enable_stdout else devnull_w
            stderr = None if enable_stderr else devnull_w
            executable = os.environ.get("SHELL")
            if platform.system() == "Windows":
                executable = None
            return subprocess.call(
                command,
                shell=True,
                executable=executable,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                cwd=cwd,
            )

    def _handle_crontab(self, data: object) -> bool:
        from crontab import CronSlices, CronTab

        entries = [self._as_mapping(item, "crontab entry") for item in self._as_list(data, "crontab")]
        any_changes_requested = False
        for entry in entries:
            entry_platform = entry.get("platform")
            if entry_platform is None or entry_platform == sys.platform:
                any_changes_requested = True
        if not any_changes_requested:
            self._console.lowinfo("No actions in crontab task match current platform, exiting")
            return True

        # Keep the legacy comment so reinstalling replaces entries created by
        # the previous Dotbot-based installer.
        cron = CronTab(user=True)
        removed = cron.remove_all(comment="dotbot")
        updated = removed > 0
        self._console.lowinfo(f"Removing {removed} old dotbot entries from users's crontab")

        for entry_idx, raw_entry in enumerate(entries):
            entry = raw_entry.copy()
            if "key" in entry and "value" in entry:
                entry_platform = entry.get("platform")
                if entry_platform is not None and entry_platform != sys.platform:
                    continue
                cron_env = cron.env
                if cron_env is None:
                    raise InstallError("Unable to read crontab environment")
                cron_env[str(entry["key"])] = str(entry["value"])
                continue

            if "time" not in entry:
                self._console.error(f"Skipping entry {entry_idx} - missing `time` config")
                continue
            time = str(entry.pop("time"))
            if "command" not in entry:
                self._console.error(f"Skipping entry {entry_idx} - missing `command` config")
                continue
            command = str(entry.pop("command"))
            job = cron.new(command=command, comment="dotbot")

            if not CronSlices.is_valid(time):
                self._console.error(f"Skipping entry {entry_idx} - invalid time {time}")
                continue
            job.setall(time)

            entry_platform = entry.pop("platform", None)
            if entry_platform is not None and entry_platform != sys.platform:
                job.enable(False)

            if entry:
                self._console.error(f"Unused config keys: {list(entry.keys())}")

            self._console.lowinfo(f"Adding command {command} at time {time} to users's crontab")
            updated = True

        if updated:
            cron.write()
        return True

    def _iter_path_options(self, data: object, directive: str) -> list[tuple[str, dict[str, object]]]:
        if isinstance(data, dict):
            return [
                (str(path), self._as_mapping(options, f"{directive} options") if isinstance(options, dict) else {})
                for path, options in data.items()
            ]
        return [(str(path), {}) for path in self._as_list(data, directive)]

    def _as_mapping(self, value: object, label: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise InstallError(f"{label} must be a mapping")
        if not all(isinstance(key, str) for key in value):
            raise InstallError(f"{label} contains a non-string key")
        return cast(dict[str, object], value)

    def _as_list(self, value: object, label: str) -> list[object]:
        if not isinstance(value, list):
            raise InstallError(f"{label} must be a list")
        return cast(list[object], value)

    def _as_string_list(self, value: object, label: str) -> list[str]:
        if not isinstance(value, list):
            raise InstallError(f"{label} must be a list")
        return [str(item) for item in value]

    def _as_mode(self, value: object, label: str) -> int:
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            return int(value, 0)
        raise InstallError(f"{label} must be an integer")
