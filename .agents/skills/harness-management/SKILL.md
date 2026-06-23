---
name: harness-management
description: Manage the srt2web harness system — features, sessions, audit trail, and health checks. Use when working with feature_list, tracking progress, starting sessions, or querying project status.
---

# Harness Management Skill

This skill guides agents through using the srt2web harness system for feature tracking, session management, and project health monitoring.

## Quick Reference

```bash
# List features
python -m harness list                    # All features
python -m harness list --status=pending   # Pending only
python -m harness list --status=done --group  # Grouped by status

# Show details
python -m harness show 106                # Feature details

# Next action
python -m harness next                    # Next feature to work on

# Statistics
python -m harness stats                   # Overview with progress bars

# Health check
python -m harness health                  # Validate DB integrity

# Search
python -m harness search "subtitle"       # Search by text

# Add feature
python -m harness add 151 my_feature "My Feature Title" --area core --priority Alta

# Update feature
python -m harness update 151 status done --agent myname
python -m harness update 151 fix '["file.py: fixed bug"]' --agent myname

# Audit trail
python -m harness audit 106              # See all changes to a feature

# Sessions
python -m harness session start --notes "Working on F151"
python -m harness session list
python -m harness session end 1 --features "151" --notes "Completed F151"

# Import/Export
python -m harness migrate                # JSON → DB
python -m harness export                 # DB → JSON
```

## Workflow for Agents

### Starting a Session

1. **Check health**: `python -m harness health`
2. **See what's next**: `python -m harness next`
3. **Start session**: `python -m harness session start --notes "Focusing on F151"`
4. **Mark feature in_progress**: `python -m harness update 151 status in_progress --agent <agent_name>`
5. **Update AGENTS.md** with your session info

### Working on a Feature

1. **Read the feature**: `python -m harness show <id>`
2. **Work on the code** (implement, test, fix)
3. **Update progress as you go**:
   ```bash
   python -m harness update <id> fix '["file.py: what changed"]' --agent <name>
   python -m harness update <id> completion_notes "Notes about what was done" --agent <name>
   ```

### Closing a Session

1. **Mark feature done**: `python -m harness update <id> status done --agent <name>`
2. **Run verification**: `.\init.ps1 -Quick` (Windows) or `./init_Mac.sh --quick` (Mac)
3. **End session**: `python -m harness session end <session_id> --features "<id>" --notes "Summary"`
4. **Check health**: `python -m harness health`
5. **Update progress/current.md**

## Database Schema

The harness uses SQLite (`harness.db`) with three tables:

### features

| Column              | Type      | Description                             |
| ------------------- | --------- | --------------------------------------- |
| id                  | TEXT PK   | Feature ID (e.g., "106", "F115")        |
| name                | TEXT      | Snake_case identifier                   |
| title               | TEXT      | Human-readable title                    |
| status              | TEXT      | pending/in_progress/done/blocked        |
| area                | TEXT      | core, frontend, security, cli-tui, etc. |
| priority            | TEXT      | Alta, Media, Baja                       |
| description         | TEXT      | Detailed description                    |
| problems_identified | JSON      | Array of problem strings                |
| acceptance          | JSON      | Array of acceptance criteria            |
| files_to_touch      | JSON      | Array of file paths                     |
| risk_assessment     | JSON      | {risk_level, mitigation[]}              |
| completed_date      | TEXT      | YYYY-MM-DD                              |
| started_in_session  | TEXT      | YYYY-MM-DD                              |
| dependencies        | JSON      | Array of feature IDs this depends on    |
| phase               | TEXT      | Phase identifier                        |
| fix                 | JSON      | Array of what was actually changed      |
| results             | JSON      | Outcome data                            |
| completion_notes    | TEXT      | Free-form notes                         |
| created_at          | TIMESTAMP | Creation time                           |
| updated_at          | TIMESTAMP | Last modification                       |

### sessions

| Column          | Type       | Description          |
| --------------- | ---------- | -------------------- |
| id              | INTEGER PK | Auto-increment       |
| date            | TEXT       | YYYY-MM-DD           |
| features_worked | JSON       | Array of feature IDs |
| notes           | TEXT       | Session summary      |
| created_at      | TIMESTAMP  | Creation time        |

### audit_log

| Column     | Type       | Description              |
| ---------- | ---------- | ------------------------ |
| id         | INTEGER PK | Auto-increment           |
| feature_id | TEXT       | Which feature changed    |
| field_name | TEXT       | Which field changed      |
| old_value  | TEXT       | Previous value           |
| new_value  | TEXT       | New value                |
| agent      | TEXT       | Who made the change      |
| timestamp  | TIMESTAMP  | When the change was made |

## Validation Rules

- **Max 1 feature in_progress** at any time
- **Valid statuses**: pending, in_progress, done, blocked
- **No duplicate IDs** (handled by PRIMARY KEY)
- **Audit trail**: All status/field changes are logged automatically
- **Auto-dates**: Setting status to `in_progress` auto-sets `started_in_session`; setting to `done` auto-sets `completed_date`

## Health Check

`python -m harness health` validates:

- Database file exists
- All required tables exist
- No invalid statuses
- No duplicate IDs
- Max 1 feature in_progress
- Feature counts by status

## Integration with Existing Harness

The harness DB replaces `feature_list.json` as the source of truth. For backward compatibility:

- `python -m harness export` generates a `feature_list_export.json`
- `python -m harness migrate` imports from `feature_list.json`
- `init.ps1` and `init_Mac.sh` validate the DB via `python -m harness health`
- `CHECKPOINTS.md` references DB health as a closure criterion

## Tips for Agents

1. **Always pass `--agent <name>`** to track who made changes
2. **Use `python -m harness stats`** at the start of each session to understand project state
3. **Use `python -m harness next`** to pick the right feature to work on
4. **Update `fix` field** as you work — don't wait until the end
5. **Check `python -m harness health`** before declaring work complete
6. **Use `python -m harness search`** to find features by area or keyword
