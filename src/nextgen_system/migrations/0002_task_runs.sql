-- Create task_runs table for orchestrator logging.
CREATE TABLE IF NOT EXISTS task_runs (
    run_id TEXT PRIMARY KEY,
    task_name TEXT NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,
    artifacts JSON,
    error TEXT
);
CREATE INDEX IF NOT EXISTS idx_task_runs_task ON task_runs(task_name, triggered_at);
