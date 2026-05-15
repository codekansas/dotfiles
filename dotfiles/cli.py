"""Command-line interface for the dotfiles installer."""

import argparse
import os
from pathlib import Path

from dotfiles import __version__
from dotfiles.config import DEFAULT_PROFILE, ConfigError, read_config, resolve_profile
from dotfiles.console import Console, Level, should_use_color
from dotfiles.installer import Installer, InstallError, InstallOptions


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("profile", nargs="?", help=f"install profile to run; defaults to {DEFAULT_PROFILE}")
    parser.add_argument("--profile", dest="profile_flag", help=f"install profile to run; defaults to {DEFAULT_PROFILE}")
    parser.add_argument("-Q", "--super-quiet", action="store_true", help="suppress almost all output")
    parser.add_argument("-q", "--quiet", action="store_true", help="suppress most output")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="enable verbose output\n-v: typical verbose\n-vv: also, set shell commands stderr/stdout to true",
    )
    parser.add_argument("-d", "--base-directory", help="execute commands from within BASEDIR", metavar="BASEDIR")
    parser.add_argument("-c", "--config-file", help="run commands given in CONFIGFILE", metavar="CONFIGFILE")
    parser.add_argument(
        "-p",
        "--plugin",
        action="append",
        dest="plugins",
        default=[],
        help="accepted for Dotbot CLI compatibility; plugins are built in",
        metavar="PLUGIN",
    )
    parser.add_argument(
        "--disable-built-in-plugins",
        action="store_true",
        help="accepted for Dotbot CLI compatibility; built-in directives are required",
    )
    parser.add_argument(
        "--plugin-dir",
        action="append",
        dest="plugin_dirs",
        default=[],
        metavar="PLUGIN_DIR",
        help="accepted for Dotbot CLI compatibility; plugins are built in",
    )
    parser.add_argument("--only", nargs="+", help="only run specified directives", metavar="DIRECTIVE")
    parser.add_argument("--except", nargs="+", dest="skip", help="skip specified directives", metavar="DIRECTIVE")
    parser.add_argument("--force-color", dest="force_color", action="store_true", help="force color output")
    parser.add_argument("--no-color", dest="no_color", action="store_true", help="disable color output")
    parser.add_argument("--version", action="store_true", help="show program's version number and exit")
    parser.add_argument(
        "-x",
        "--exit-on-failure",
        dest="exit_on_failure",
        action="store_true",
        help="exit after first failed directive",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the installer CLI."""
    parser = build_parser()
    options = parser.parse_args(argv)
    console = Console(use_color=False)

    if options.force_color and options.no_color:
        console.error("`--force-color` and `--no-color` cannot both be provided")
        return 1
    if options.profile is not None and options.profile_flag is not None and options.profile != options.profile_flag:
        console.error("Positional profile and `--profile` cannot disagree")
        return 1

    console.use_color(should_use_color(force_color=options.force_color, no_color=options.no_color))
    if options.version:
        console.info(f"dotfiles installer version {__version__}")
        return 0

    if options.super_quiet:
        console.set_level(Level.WARNING)
    if options.quiet:
        console.set_level(Level.INFO)
    if options.verbose > 0:
        console.set_level(Level.DEBUG)

    if options.disable_built_in_plugins:
        console.warning("Built-in installer directives cannot be disabled")
    if options.plugins or options.plugin_dirs:
        console.debug("External Dotbot plugin flags are accepted for compatibility and ignored")

    profile_name = options.profile_flag or options.profile or DEFAULT_PROFILE
    config_file = _resolve_config_file(options.config_file)
    base_directory = _resolve_base_directory(options.base_directory, config_file)
    try:
        tasks = read_config(config_file)
        profile = resolve_profile(tasks, profile_name)
        if not tasks:
            console.warning("Configuration file is empty, no work to do")

        os.chdir(base_directory)
        installer = Installer(
            base_directory=base_directory,
            console=console,
            options=InstallOptions(
                only=set(options.only) if options.only else None,
                skip=set(options.skip) if options.skip else None,
                profile=profile.name,
                profile_skip=profile.skip,
                exit_on_failure=options.exit_on_failure,
                verbose=options.verbose,
            ),
        )
        success = installer.dispatch(tasks)
        if success:
            console.info("\n==> All tasks executed successfully")
            return 0
        raise InstallError("\n==> Some tasks were not executed successfully")
    except (ConfigError, InstallError) as exc:
        console.error(exc)
        return 1
    except KeyboardInterrupt:
        console.error("\n==> Operation aborted")
        return 1


def _resolve_config_file(config_file: str | None) -> Path:
    if config_file is None:
        return Path("install.conf.yaml").resolve()
    return Path(config_file).expanduser().resolve()


def _resolve_base_directory(base_directory: str | None, config_file: Path) -> Path:
    if base_directory is None:
        return config_file.parent.resolve()
    return Path(base_directory).expanduser().resolve()
