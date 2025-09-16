"""CLI entrypoint for next-generation orchestrator."""

from __future__ import annotations

import argparse
import json
from typing import Optional

from nextgen_system.orchestration.registry import TaskRegistry
from nextgen_system.orchestration.tasks import register_tasks


def build_registry() -> TaskRegistry:
    registry = TaskRegistry()
    register_tasks(registry)
    return registry


def list_tasks(registry: TaskRegistry) -> None:
    for name in registry.list_tasks():
        meta = registry.get(name)
        print(f"{name}: {meta['description']}")


def run_task(registry: TaskRegistry, name: str) -> None:
    run_id = registry.run_task(name)
    print(json.dumps({"task": name, "run_id": run_id}))


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Next-gen system orchestrator")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List registered tasks")
    run_parser = subparsers.add_parser("run", help="Run a task by name")
    run_parser.add_argument("name", help="Task name")

    args = parser.parse_args(argv)
    registry = build_registry()

    if args.command == "list":
        list_tasks(registry)
    elif args.command == "run":
        run_task(registry, args.name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
