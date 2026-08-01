#!/usr/bin/env python3
"""Run read-only and emergency Lakemeter upgrade commands locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from databricks.sdk import WorkspaceClient

from upgrader.runner import run_command


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("status", "plan", "doctor", "rollback"),
    )
    parser.add_argument("--app-name", default="lakemeter")
    parser.add_argument("--profile")
    parser.add_argument("--payload-root", type=Path, default=Path("."))
    args = parser.parse_args()

    client = (
        WorkspaceClient(profile=args.profile)
        if args.profile
        else WorkspaceClient()
    )
    result = run_command(
        workspace_client=client,
        command=args.command,
        app_name=args.app_name,
        payload_root=args.payload_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("status") == "blocked":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

