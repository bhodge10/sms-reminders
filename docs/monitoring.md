# Multi-Agent Monitoring System

Dashboard at `/admin/monitoring`. Four agents run on Celery schedules:

1. **Agent 1 - Interaction Monitor** (`agents/interaction_monitor.py`) - Detects anomalies: user confusion, parsing failures, error responses, context loss, flow violations
2. **Agent 2 - Issue Validator** (`agents/issue_validator.py`) - Validates issues, filters false positives, optional AI analysis
3. **Agent 3 - Resolution Tracker** (`agents/resolution_tracker.py`) - Health score (0-100), resolution tracking, weekly reports
4. **Agent 4 - Fix Planner** (`agents/fix_planner.py`) - Identifies affected files, generates Claude Code prompts for fixes

**Celery schedule:** Hourly critical check, every 4h Agent 1, every 6h Agent 2, daily 6AM UTC full pipeline, weekly Monday report.

**Manual triggers:** Dashboard button, `GET /admin/pipeline/run?hours=24`, `python -m agents.fix_planner --issue 123`

**Issue types:** `user_confusion`, `error_response`, `parsing_failure`, `timezone_issue`, `failed_action`, `action_not_found`, `confidence_rejection`, `repeated_attempts`, `delivery_failure`, `context_loss`, `flow_violation`

**DB tables:** `monitoring_issues`, `monitoring_runs`, `issue_patterns`, `issue_pattern_links`, `validation_runs`, `issue_resolutions`, `pattern_resolutions`, `health_snapshots`, `fix_proposals`, `fix_proposal_runs`
