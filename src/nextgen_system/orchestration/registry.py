"""Task registry and execution logging for the orchestration layer."""

from __future__ import annotations

import json
import traceback
import uuid
from datetime import datetime
from typing import Callable, Dict, Iterable, Optional

from nextgen_system.persistence.database import get_database


class TaskRegistry:
    """Register tasks and persist execution metadata to ``task_runs``."""

    def __init__(self):
        self._tasks: Dict[str, Dict] = {}

    def register(
        self,
        name: str,
        func: Callable[..., Optional[Dict]],
        *,
        cadence: Optional[str] = None,
        dependencies: Optional[Iterable[str]] = None,
        description: str = "",
    ) -> None:
        self._tasks[name] = {
            "func": func,
            "cadence": cadence,
            "dependencies": list(dependencies or []),
            "description": description,
        }

    def list_tasks(self):
        return sorted(self._tasks.keys())

    def get(self, name: str) -> Dict:
        return self._tasks[name]

    def run_task(self, name: str, *args, _executed=None, **kwargs) -> str:
        _executed = _executed or set()
        if name in _executed:
            return ""
        task = self._tasks.get(name)
        if not task:
            raise KeyError(f"Unknown task: {name}")

        for dep in task["dependencies"]:
            self.run_task(dep, _executed=_executed)

        run_id = uuid.uuid4().hex
        db = get_database()
        db.execute(
            "INSERT INTO task_runs(run_id, task_name, status, triggered_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (run_id, name, "RUNNING"),
        )

        status = "SUCCESS"
        artifacts = None
        error = None

        try:
            result = task["func"](*args, **kwargs)
            if result is not None:
                artifacts = json.dumps(result)
        except Exception as exc:  # pragma: no cover
            status = "FAILED"
            error = f"{exc}\n{traceback.format_exc()}"
        finally:
            db.execute(
                "UPDATE task_runs SET completed_at = ?, status = ?, artifacts = ?, error = ? WHERE run_id = ?",
                (
                    datetime.utcnow(),
                    status,
                    artifacts,
                    error,
                    run_id,
                ),
            )

        if status == "FAILED":
            raise RuntimeError(f"Task {name} failed; run_id={run_id}")

        _executed.add(name)
        return run_id
