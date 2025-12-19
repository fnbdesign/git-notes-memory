"""Main entry point for git_notes_memory CLI."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    """Application entry point.

    Args:
        argv: Command-line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        prog="git-notes-memory",
        description="Git-native, semantically-searchable memory storage",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["status", "reindex", "verify", "gc"],
        help="Memory command to run",
    )

    args = parser.parse_args(argv)

    if args.version:
        from git_notes_memory import __version__

        print(f"git-notes-memory {__version__}")
        return 0

    if args.command is None:
        parser.print_help()
        return 0

    # Commands will be implemented in later phases
    print(f"Command '{args.command}' not yet implemented")
    return 1


if __name__ == "__main__":
    sys.exit(main())
