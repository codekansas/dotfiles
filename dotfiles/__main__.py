"""Run the dotfiles installer as a module."""

from dotfiles.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
