"""Console output helpers for installer status messages."""

import os
import sys
from enum import IntEnum


class Level(IntEnum):
    """Status levels matching the previous installer output model."""

    DEBUG = 10
    LOWINFO = 20
    INFO = 30
    WARNING = 40
    ERROR = 50


class Color:
    """ANSI color escape sequences used by Dotbot-style output."""

    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"


class Console:
    """Small stdout logger with Dotbot-compatible levels and colors."""

    def __init__(self, level: Level = Level.LOWINFO, use_color: bool = True) -> None:
        self._level = level
        self._use_color = use_color

    def set_level(self, level: Level) -> None:
        self._level = level

    def use_color(self, use_color: bool) -> None:
        self._use_color = use_color

    def debug(self, message: object) -> None:
        self.log(Level.DEBUG, message)

    def lowinfo(self, message: object) -> None:
        self.log(Level.LOWINFO, message)

    def info(self, message: object) -> None:
        self.log(Level.INFO, message)

    def warning(self, message: object) -> None:
        self.log(Level.WARNING, message)

    def error(self, message: object) -> None:
        self.log(Level.ERROR, message)

    def log(self, level: Level, message: object) -> None:
        if level < self._level:
            return
        sys.stdout.write(f"{self._color(level)}{message}{self._reset()}\n")
        sys.stdout.flush()

    def _color(self, level: Level) -> str:
        if not self._use_color:
            return ""
        if level < Level.DEBUG:
            return ""
        if Level.DEBUG <= level < Level.LOWINFO:
            return Color.YELLOW
        if Level.LOWINFO <= level < Level.INFO:
            return Color.BLUE
        if Level.INFO <= level < Level.WARNING:
            return Color.GREEN
        if Level.WARNING <= level < Level.ERROR:
            return Color.MAGENTA
        return Color.RED

    def _reset(self) -> str:
        if not self._use_color:
            return ""
        return Color.RESET


def should_use_color(*, force_color: bool, no_color: bool) -> bool:
    """Resolve color behavior from flags and terminal environment."""
    if force_color:
        return True
    if no_color:
        return False
    if os.environ.get("NO_COLOR") is not None or os.environ.get("TERM") == "dumb":
        return False
    return sys.stdout.isatty()
