"""In-app scheduler that periodically dispatches due reports."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.services import report_service

logger = logging.getLogger("app.scheduler")

_scheduler: BackgroundScheduler | None = None


def _run_dispatch() -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        sent = report_service.dispatch_due_reports(db)
        if sent:
            logger.info("Dispatched scheduled reports: %s", ", ".join(sent))
    except Exception:  # noqa: BLE001 - a scheduler tick must never crash the app
        logger.exception("Scheduled report dispatch failed")
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    # Check every 15 minutes; dispatch_due_reports decides what is actually due.
    _scheduler.add_job(_run_dispatch, "interval", minutes=15, id="report_dispatch", replace_existing=True)
    _scheduler.start()
    logger.info("Report scheduler started (checks every 15 minutes)")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
