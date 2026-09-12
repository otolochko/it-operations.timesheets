"""Incremental Jira worklog synchronization."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.jira_http import JiraClient
from app.core.worklog_time import work_date_from_jira_json
from app.models import Issue, SyncRun, SyncSchedule, SyncState, Worklog


def get_or_create_schedule(db: Session) -> SyncSchedule:
    schedule = db.get(SyncSchedule, 1)
    if schedule is None:
        schedule = SyncSchedule(
            id=1,
            cron_expression=settings.sync_default_cron,
            project_keys=",".join(settings.jira_project_keys),
            jql_filter=None,
            updated_at=_utcnow(),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
    return schedule


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Jira timestamp must include an offset: {value!r}")
    return parsed


def _epoch_millis(value: datetime | None) -> int:
    if value is None:
        return 0
    if value.tzinfo is None:
        # SQLite drops timezone information; stored watermarks are UTC.
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def _watermark_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _change_id(change: dict) -> str:
    value = change.get("worklogId", change.get("id"))
    if value is None:
        raise ValueError(f"Worklog change is missing its id: {change!r}")
    return str(value)


def _append_log(db: Session, run: SyncRun, message: str) -> None:
    run.log_text = f"{run.log_text or ''}{message}\n"
    db.commit()


def _progress(
    db: Session,
    run: SyncRun,
    *,
    phase: str,
    current: int,
    total: int | None,
    log: str | None = None,
) -> None:
    run.progress_phase = phase
    run.progress_current = current
    run.progress_total = total
    if log is not None:
        run.log_text = f"{run.log_text or ''}{log}\n"
    db.commit()


def _issue_key_from_worklog(worklog: dict) -> str | None:
    key = worklog.get("issueKey")
    if key:
        return str(key)
    issue = worklog.get("issue")
    if isinstance(issue, dict) and issue.get("key"):
        return str(issue["key"])
    return None


def _project_from_key(issue_key: str | None) -> str | None:
    if not issue_key or "-" not in issue_key:
        return None
    return issue_key.split("-", 1)[0]


def run_sync(db: Session, jira_client: JiraClient | None = None) -> SyncRun:
    """Run one atomic incremental synchronization.

    The initial SyncRun commit is deliberately separate so status readers can
    observe the running job. All synchronized data and the cursor commit once.
    """
    run = SyncRun(
        started_at=_utcnow(),
        status="running",
        worklogs_upserted=0,
        worklogs_deleted=0,
        log_text="Sync started\n",
    )
    db.add(run)
    db.commit()
    run_id = run.id

    client = jira_client or JiraClient()
    owns_client = jira_client is None

    try:
        schedule = get_or_create_schedule(db)

        state = db.get(SyncState, 1)
        if state is None:
            state = SyncState(id=1, last_watermark=None)
            db.add(state)
            # Persist the required singleton without moving its cursor. This
            # is setup state, not part of the synchronized-data transaction.
            db.commit()

        since = _epoch_millis(state.last_watermark)
        updated_changes, updated_until = client.get_updated_worklog_ids(
            since,
            on_page=lambda page, count: _progress(
                db,
                run,
                phase="Fetching updated worklog ids",
                current=count,
                total=None,
                log=f"Updated worklog ids: page {page}, {count} so far",
            ),
        )
        _append_log(db, run, f"Fetched {len(updated_changes)} updated worklog ids")

        deleted_changes = client.get_deleted_worklog_ids(
            since,
            on_page=lambda page, count: _progress(
                db,
                run,
                phase="Fetching deleted worklog ids",
                current=count,
                total=None,
                log=f"Deleted worklog ids: page {page}, {count} so far",
            ),
        )
        _append_log(db, run, f"Fetched {len(deleted_changes)} deleted worklog ids")

        updated_ids = list(dict.fromkeys(_change_id(item) for item in updated_changes))
        worklogs = client.get_worklogs_by_ids(
            updated_ids,
            on_page=lambda page, count: _progress(
                db,
                run,
                phase="Fetching full worklogs",
                current=count,
                total=len(updated_ids),
                log=f"Fetched worklogs: batch {page}, {count} so far",
            ),
        )
        _append_log(db, run, f"Fetched {len(worklogs)} full worklogs")

        allowed_issue_ids: set[str] | None = None
        if schedule.jql_filter:
            allowed_issue_ids = client.search_issue_ids(
                schedule.jql_filter,
                on_page=lambda page, count: _progress(
                    db,
                    run,
                    phase="Resolving JQL filter",
                    current=count,
                    total=None,
                    log=f"JQL search: page {page}, {count} issues so far",
                ),
            )
            _append_log(db, run, f"JQL filter matched {len(allowed_issue_ids)} issues")
            allowed_projects: set[str] = set()
        else:
            allowed_projects = {key for key in schedule.project_keys.split(",") if key}

        # Resolve the set of unique issue ids this run needs metadata for
        # up front, so the fetch loop below has a known total for progress
        # reporting instead of an indeterminate count.
        candidate_issue_ids: list[str] = []
        seen_issue_ids: set[str] = set()
        for worklog_json in worklogs:
            issue_id = str(worklog_json["issueId"])
            if issue_id in seen_issue_ids:
                continue

            if allowed_issue_ids is not None:
                if issue_id not in allowed_issue_ids:
                    continue
            else:
                issue_key = _issue_key_from_worklog(worklog_json)
                project_hint = _project_from_key(issue_key)
                if allowed_projects and project_hint and project_hint not in allowed_projects:
                    continue

            seen_issue_ids.add(issue_id)
            candidate_issue_ids.append(issue_id)

        issue_payloads: dict[str, dict | None] = {}
        total_issues = len(candidate_issue_ids)
        # Absolute cadence, not a percentage of total: on a large first sync
        # (thousands of issues), a percentage-based step could stay silent
        # for minutes even though every request is succeeding.
        progress_step = min(25, max(1, total_issues))
        for i, issue_id in enumerate(candidate_issue_ids, start=1):
            issue_payloads[issue_id] = client.get_issue(issue_id)
            if i % progress_step == 0 or i == total_issues:
                _progress(
                    db,
                    run,
                    phase="Fetching issue metadata",
                    current=i,
                    total=total_issues,
                    log=f"Fetching issue metadata: {i}/{total_issues}",
                )

        in_scope: list[tuple[dict, dict]] = []
        for worklog_json in worklogs:
            issue_id = str(worklog_json["issueId"])
            if issue_id not in issue_payloads:
                continue
            issue_json = issue_payloads[issue_id]
            if issue_json is None:
                continue

            if allowed_issue_ids is None:
                fields = issue_json.get("fields", {})
                project_key = str(fields["project"]["key"])
                if allowed_projects and project_key not in allowed_projects:
                    continue
            in_scope.append((worklog_json, issue_json))

        _progress(
            db,
            run,
            phase="Writing changes to database",
            current=0,
            total=len(in_scope),
        )

        now = _utcnow()

        # Preload every Issue/Worklog row this run will touch in one query
        # each, instead of one SELECT per worklog -- a sync batch can cover
        # hundreds of worklogs across a much smaller set of issues.
        issue_ids = {str(worklog_json["issueId"]) for worklog_json, _ in in_scope}
        issue_rows: dict[str, Issue] = (
            {issue.id: issue for issue in db.scalars(select(Issue).where(Issue.id.in_(issue_ids)))}
            if issue_ids
            else {}
        )

        worklog_ids = {str(worklog_json["id"]) for worklog_json, _ in in_scope}
        deleted_ids = {_change_id(change) for change in deleted_changes}
        all_worklog_ids = worklog_ids | deleted_ids
        worklog_rows: dict[str, Worklog] = (
            {
                worklog.id: worklog
                for worklog in db.scalars(select(Worklog).where(Worklog.id.in_(all_worklog_ids)))
            }
            if all_worklog_ids
            else {}
        )

        for worklog_json, issue_json in in_scope:
            issue_id = str(worklog_json["issueId"])
            fields = issue_json.get("fields", {})
            issue = issue_rows.get(issue_id)
            if issue is None:
                issue = Issue(id=issue_id)
                db.add(issue)
                issue_rows[issue_id] = issue
            issue.key = str(issue_json["key"])
            issue.project_key = str(fields["project"]["key"])
            issue.summary = str(fields.get("summary") or "")
            issue.updated_at = now

            started = _parse_datetime(worklog_json["started"])
            offset = started.utcoffset()
            if offset is None:
                raise ValueError("Jira worklog 'started' must include a numeric offset")

            worklog_id = str(worklog_json["id"])
            worklog = worklog_rows.get(worklog_id)
            if worklog is None:
                worklog = Worklog(id=worklog_id)
                db.add(worklog)
                worklog_rows[worklog_id] = worklog
            author = worklog_json.get("author") or {}
            worklog.issue_id = issue_id
            worklog.author_account_id = str(author["accountId"])
            worklog.author_display_name = str(author.get("displayName") or "")
            worklog.time_spent_seconds = int(worklog_json["timeSpentSeconds"])
            worklog.started = started
            worklog.started_utc_offset = int(offset.total_seconds())
            worklog.work_date = work_date_from_jira_json(worklog_json)
            worklog.updated_at = _parse_datetime(worklog_json["updated"])

        deleted_count = 0
        for change in deleted_changes:
            existing = worklog_rows.get(_change_id(change))
            if existing is not None:
                db.delete(existing)
                deleted_count += 1

        run.worklogs_upserted = len(in_scope)
        run.worklogs_deleted = deleted_count
        _append_log(db, run, f"Upserted {len(in_scope)} worklogs")
        _append_log(db, run, f"Deleted {deleted_count} worklogs")

        deleted_until = getattr(client, "last_deleted_until", None)
        until_values = [v for v in (updated_until, deleted_until) if v is not None]
        if until_values:
            state.last_watermark = _watermark_datetime(max(until_values))

        run.status = "success"
        run.finished_at = _utcnow()
        run.progress_phase = "Completed"
        run.progress_current = run.progress_total or 0
        _append_log(db, run, "Sync completed successfully")
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:
        progress_log = run.log_text
        db.rollback()
        failed_run = db.get(SyncRun, run_id)
        if failed_run is None:
            raise RuntimeError(f"Sync run {run_id} disappeared") from exc
        failed_run.status = "failed"
        failed_run.finished_at = _utcnow()
        failed_run.error = str(exc) or exc.__class__.__name__
        failed_run.log_text = progress_log
        _append_log(db, failed_run, f"Sync failed: {failed_run.error}")
        db.commit()
        raise
    finally:
        if owns_client:
            client.close()
