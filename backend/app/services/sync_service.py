"""Incremental Jira worklog synchronization."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.jira_http import JiraClient
from app.core.worklog_time import work_date_from_jira_json
from app.models import Issue, SyncRun, SyncSchedule, SyncState, Worklog


def reserve_sync_run(db: Session) -> tuple[SyncRun, bool]:
    """Atomically reserve the sole permitted running sync.

    The partial unique index on ``sync_runs.status`` is the arbiter here, not
    an application-level read followed by an insert.  Therefore independent
    web workers and APScheduler processes cannot both start a Jira sync.
    """
    run = SyncRun(
        started_at=_utcnow(),
        status="running",
        worklogs_upserted=0,
        worklogs_deleted=0,
        log_text="Sync started\n",
    )
    try:
        db.add(run)
        db.commit()
        db.refresh(run)
        return run, True
    except IntegrityError:
        db.rollback()
        running = db.scalars(
            select(SyncRun)
            .where(SyncRun.status == "running")
            .order_by(SyncRun.id.desc())
        ).first()
        if running is None:
            # A database that reports a uniqueness conflict must expose the
            # conflicting committed row after the transaction rollback.
            raise RuntimeError("Sync reservation conflicted without a running sync")
        return running, False


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


class SyncCancelled(Exception):
    """Raised when a user requests cancellation of an in-progress sync run."""


def _append_log(db: Session, run: SyncRun, message: str) -> None:
    """Publish one log line without committing the sync transaction."""
    status_db = _status_session(db)
    if status_db is None:
        # An in-memory SQLite database has one physical connection, so a
        # second Session would commit the sync transaction too.  Keep tests
        # and other such ephemeral deployments safe rather than live.
        run.log_text = f"{run.log_text or ''}{message}\n"
        return
    try:
        persisted_run = status_db.get(SyncRun, run.id)
        if persisted_run is None:
            raise RuntimeError(f"Sync run {run.id} disappeared")
        persisted_run.log_text = f"{persisted_run.log_text or ''}{message}\n"
        status_db.commit()
    finally:
        status_db.close()


def _status_session(db: Session) -> Session | None:
    """Return an isolated short-lived status session when one is possible."""
    bind = db.get_bind()
    # SQLAlchemy's in-memory SQLite URLs are backed by a single connection in
    # this project’s tests.  A "separate" Session there is not a separate
    # transaction and may commit staged worklogs, so deliberately fall back.
    database = getattr(getattr(bind, "url", None), "database", None)
    if bind.dialect.name == "sqlite" and database in (None, ":memory:"):
        return None
    return Session(bind=bind, autoflush=False)


def _progress(
    db: Session,
    run: SyncRun,
    *,
    phase: str,
    current: int,
    total: int | None,
    log: str | None = None,
) -> None:
    status_db = _status_session(db)
    if status_db is None:
        run.progress_phase = phase
        run.progress_current = current
        run.progress_total = total
        if log is not None:
            run.log_text = f"{run.log_text or ''}{log}\n"
        cancel_requested = run.cancel_requested
    else:
        try:
            persisted_run = status_db.get(SyncRun, run.id)
            if persisted_run is None:
                raise RuntimeError(f"Sync run {run.id} disappeared")
            persisted_run.progress_phase = phase
            persisted_run.progress_current = current
            persisted_run.progress_total = total
            if log is not None:
                persisted_run.log_text = f"{persisted_run.log_text or ''}{log}\n"
            cancel_requested = persisted_run.cancel_requested
            status_db.commit()
        finally:
            status_db.close()
    if cancel_requested:
        raise SyncCancelled()


def _finish_terminal_run(
    db: Session, run_id: int, *, status: str, error: str | None, log_message: str
) -> SyncRun:
    """Persist a cancelled/failed run after the data transaction rolled back."""
    status_db = _status_session(db)
    owns_status_session = status_db is not None
    if status_db is None:
        status_db = db
    try:
        run = status_db.get(SyncRun, run_id, with_for_update=True)
        if run is None:
            raise RuntimeError(f"Sync run {run_id} disappeared")
        run.status = status
        run.finished_at = _utcnow()
        run.error = error
        run.log_text = f"{run.log_text or ''}{log_message}\n"
        status_db.commit()
    finally:
        if owns_status_session:
            status_db.close()
    result = db.get(SyncRun, run_id)
    if result is None:
        raise RuntimeError(f"Sync run {run_id} disappeared")
    return result


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


def run_sync(
    db: Session, jira_client: JiraClient | None = None, *, run_id: int | None = None
) -> SyncRun:
    """Run one atomic incremental synchronization.

    The initial SyncRun reservation is deliberately committed separately so
    status readers can observe the running job and its database unique index
    protects every trigger path. All synchronized data, cursor movement, and
    terminal success state commit once.

    Progress and logs are published through isolated short-lived status
    sessions.  The main transaction never commits them independently, so
    staged worklogs and the watermark remain atomic.
    """
    if run_id is None:
        run, reserved = reserve_sync_run(db)
        if not reserved:
            return run
        run_id = run.id
    else:
        run = db.get(SyncRun, run_id)
        if run is None:
            raise RuntimeError(f"Sync run {run_id} does not exist")
        if run.status != "running":
            return run

    client = jira_client or JiraClient()
    owns_client = jira_client is None

    try:
        schedule = get_or_create_schedule(db)

        state = db.get(SyncState, 1)
        if state is None:
            state = SyncState(id=1, last_watermark=None)
            db.add(state)

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

        # Resolve the set of unique issue ids this run touches, up front so
        # we know which ones we already have locally.
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

        # Issue key/summary/project rarely change, so an issue already
        # synced in a prior run doesn't need refetching -- only ask Jira
        # about ones we've never seen, batched via `id in (...)` search
        # instead of one GET per issue.
        issue_rows: dict[str, Issue] = {}
        for start in range(0, len(candidate_issue_ids), 10000):
            chunk = candidate_issue_ids[start : start + 10000]
            for issue in db.scalars(select(Issue).where(Issue.id.in_(chunk))):
                issue_rows[issue.id] = issue
        missing_issue_ids = [i for i in candidate_issue_ids if i not in issue_rows]

        issue_payloads: dict[str, dict] = {}
        total_missing = len(missing_issue_ids)
        if total_missing:
            _append_log(
                db,
                run,
                f"Fetching metadata for {total_missing} new issues "
                f"({len(candidate_issue_ids) - total_missing} already known locally)",
            )
            fetched_issues = client.get_issues_by_ids(
                missing_issue_ids,
                on_page=lambda page, count: _progress(
                    db,
                    run,
                    phase="Fetching issue metadata",
                    current=count,
                    total=total_missing,
                    log=f"Fetching issue metadata: {count}/{total_missing}",
                ),
            )
            issue_payloads = {str(item["id"]): item for item in fetched_issues}

        in_scope: list[tuple[dict, dict | None]] = []
        for worklog_json in worklogs:
            issue_id = str(worklog_json["issueId"])
            known_issue = issue_rows.get(issue_id)
            issue_json = issue_payloads.get(issue_id)
            if known_issue is None and issue_json is None:
                continue  # not a candidate, or deleted upstream

            if allowed_issue_ids is None:
                project_key = (
                    known_issue.project_key
                    if known_issue is not None
                    else str(issue_json["fields"]["project"]["key"])
                )
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

        worklog_ids = {str(worklog_json["id"]) for worklog_json, _ in in_scope}
        deleted_ids = {_change_id(change) for change in deleted_changes}
        all_worklog_ids = worklog_ids | deleted_ids
        all_worklog_ids_list = list(all_worklog_ids)
        worklog_rows: dict[str, Worklog] = {}
        for start in range(0, len(all_worklog_ids_list), 10000):
            chunk = all_worklog_ids_list[start : start + 10000]
            for worklog in db.scalars(select(Worklog).where(Worklog.id.in_(chunk))):
                worklog_rows[worklog.id] = worklog

        for worklog_json, issue_json in in_scope:
            issue_id = str(worklog_json["issueId"])
            issue = issue_rows.get(issue_id)
            if issue is None:
                issue = Issue(id=issue_id)
                db.add(issue)
                issue_rows[issue_id] = issue
            if issue_json is not None:
                # None means this issue was already known locally (not
                # refetched this run) -- its key/summary/project are left
                # as they were.
                fields = issue_json.get("fields", {})
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

        _append_log(db, run, f"Upserted {len(in_scope)} worklogs")
        _append_log(db, run, f"Deleted {deleted_count} worklogs")

        deleted_until = getattr(client, "last_deleted_until", None)
        until_values = [v for v in (updated_until, deleted_until) if v is not None]
        if until_values:
            state.last_watermark = _watermark_datetime(max(until_values))

        # Flush staged data, then lock and refresh the run.  This picks up all
        # independently committed progress/log entries and makes the final
        # cancellation check atomic with the success transition.  The lock is
        # held only for this final database commit, never over Jira I/O.
        db.flush()
        db.refresh(run, with_for_update=True)
        if run.cancel_requested:
            raise SyncCancelled()
        run.worklogs_upserted = len(in_scope)
        run.worklogs_deleted = deleted_count
        run.status = "success"
        run.finished_at = _utcnow()
        run.progress_phase = "Completed"
        run.progress_current = run.progress_total or 0
        run.log_text = f"{run.log_text or ''}Sync completed successfully\n"
        db.commit()
        db.refresh(run)
        return run
    except SyncCancelled:
        db.rollback()
        return _finish_terminal_run(
            db,
            run_id,
            status="cancelled",
            error=None,
            log_message="Sync cancelled by user",
        )
    except Exception as exc:
        db.rollback()
        error = str(exc) or exc.__class__.__name__
        _finish_terminal_run(
            db,
            run_id,
            status="failed",
            error=error,
            log_message=f"Sync failed: {error}",
        )
        raise
    finally:
        if owns_client:
            client.close()
