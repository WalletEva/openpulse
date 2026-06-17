"""Scheduler engine wrapping APScheduler."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class SchedulerEngine:
    """
    Collection task scheduler using APScheduler.

    Supports:
    - Cron-based scheduled collection
    - Manual immediate collection
    - Job management (add, remove, pause, resume)
    """

    def __init__(self, max_instances: int = 3):
        self.scheduler = BackgroundScheduler(
            job_defaults={
                "max_instances": max_instances,
                "coalesce": True,
                "misfire_grace_time": 300,
            }
        )
        self._started = False

    def start(self) -> None:
        """Start the scheduler."""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        if self._started:
            self.scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("Scheduler shutdown")

    def add_collection_job(
        self,
        job_id: str,
        cron_expr: str,
        source_config: dict[str, Any],
        adapter_name: str = "rsshub",
    ) -> str:
        """
        Add a scheduled collection job.

        Args:
            job_id: Unique job identifier
            cron_expr: Cron expression (e.g. '*/30 * * * *' for every 30 minutes)
            source_config: Source configuration dict
            adapter_name: Adapter to use

        Returns:
            The job ID.
        """
        trigger = CronTrigger.from_crontab(cron_expr)

        self.scheduler.add_job(
            func=self._run_collection,
            trigger=trigger,
            id=job_id,
            name=f"collect:{source_config.get('source_name', job_id)}",
            kwargs={
                "source_config": source_config,
                "adapter_name": adapter_name,
            },
            replace_existing=True,
        )
        logger.info(f"Added scheduled job: {job_id} with cron: {cron_expr}")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
            return True
        except Exception:
            return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        try:
            self.scheduler.pause_job(job_id)
            return True
        except Exception:
            return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        try:
            self.scheduler.resume_job(job_id)
            return True
        except Exception:
            return False

    def run_now(self, job_id: str) -> bool:
        """Trigger a job to run immediately."""
        try:
            self.scheduler.modify_job(job_id, next_run_time=datetime.now())
            return True
        except Exception:
            return False

    def get_jobs(self) -> list[dict[str, Any]]:
        """Get all scheduled jobs with their status."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs

    def _run_collection(
        self,
        source_config: dict[str, Any],
        adapter_name: str,
    ) -> None:
        """Execute a collection job (called by the scheduler)."""
        import asyncio
        from openpulse.collector.adapters import CustomRSSCollector, RSSHubCollector
        from openpulse.storage.database import get_session
        from openpulse.storage.repositories.article_repo import ArticleRepository

        async def _collect() -> None:
            if adapter_name == "rsshub":
                collector = RSSHubCollector()
            else:
                collector = CustomRSSCollector()

            result = await collector.collect(source_config)

            if result.success:
                from openpulse.collector.converter import pydantic_list_to_orm
                orm_articles = pydantic_list_to_orm(result.articles)

                session = get_session()
                try:
                    repo = ArticleRepository(session)
                    new_articles = repo.add_many(orm_articles)
                    session.commit()
                    logger.info(
                        f"Collection completed: {result.source} - "
                        f"{result.count} articles ({len(new_articles)} new)"
                    )
                except Exception as e:
                    session.rollback()
                    logger.error(f"Collection save failed: {result.source} - {e}")
                finally:
                    session.close()
            else:
                logger.error(f"Collection failed: {result.source} - {result.error}")

        asyncio.run(_collect())

    @property
    def is_running(self) -> bool:
        return self._started
