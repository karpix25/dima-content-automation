# Lessons
- For owner-specific service alerts, verify both the configured Telegram chat IDs and the runtime notification path before assuming messages will be delivered.
- NotebookLM auth alerts must link directly to the noVNC browser login page, not a generic service/API root URL.
- If noVNC auth turns black during Google verification, restart the auth browser/container and verify the VNC page before asking the user to retry.
- Before calling a UI generation button safe, verify backend concurrency guards for long-running video jobs, not only successful single-job execution.
- Do not treat stale format jobs with status `ready` as active video renders; only queued, processing, and submitted should block new long-running video jobs.
- If the product expects one explicit format request at a time, block every new format job while any format job is queued, processing, or submitted.
