#!/usr/bin/env python3
"""Hook: Sync memory index on session end.

This hook performs a lightweight incremental sync of the memory index
when a Claude Code session ends. This ensures any memories captured
during the session are properly indexed for future retrieval.
"""

from __future__ import annotations

import json
import sys


def sync_index() -> dict:
    """Perform incremental index sync.

    Returns dict with sync result.
    """
    try:
        from git_notes_memory import get_sync_service

        sync = get_sync_service()
        stats = sync.incremental_sync()

        return {
            "success": True,
            "stats": {
                "scanned": stats.get("scanned", 0),
                "added": stats.get("added", 0),
                "updated": stats.get("updated", 0),
            }
        }

    except ImportError:
        # Library not installed, skip silently
        return {"success": True, "skipped": True}
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main() -> None:
    """Main hook entry point."""
    # Read hook input from stdin (may be empty for stop hook)
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        input_data = {}

    # Perform sync
    result = sync_index()

    # Output result
    output = {"continue": True}

    if result.get("skipped"):
        # Silently skip if library not installed
        pass
    elif result.get("success"):
        stats = result.get("stats", {})
        if stats.get("added", 0) > 0 or stats.get("updated", 0) > 0:
            output["message"] = f"Memory index synced: +{stats.get('added', 0)} new, ~{stats.get('updated', 0)} updated"
    else:
        output["warning"] = f"Memory sync failed: {result.get('error', 'Unknown error')}"

    print(json.dumps(output))


if __name__ == "__main__":
    main()
