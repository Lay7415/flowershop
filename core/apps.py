# core/apps.py
import logging
import os
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Основные настройки и задачи'

    def ready(self):
        # Avoid running scheduler in auto-reload mode
        if os.environ.get('RUN_MAIN', None) != 'true':
            return

        try:
            self.start_scheduler()
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")

    def start_scheduler(self):
        from django_apscheduler.jobstores import DjangoJobStore
        from apscheduler.schedulers.background import BackgroundScheduler
        from . import tasks

        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Add tasks with error handling
        try:
            scheduler.add_job(
                tasks.assign_florist_task,
                trigger='interval',
                minutes=5,  # Increased interval
                id='assign_florist_job',
                max_instances=1,
                replace_existing=True,
                coalesce=True,  # Combine missed runs
                misfire_grace_time=300  # 5 minute grace time
            )
            logger.info("Added assign_florist_job to scheduler")

            scheduler.add_job(
                tasks.assign_courier_task,
                trigger='interval',
                minutes=5,  # Increased interval
                id='assign_courier_job',
                max_instances=1,
                replace_existing=True,
                coalesce=True,  # Combine missed runs
                misfire_grace_time=300  # 5 minute grace time
            )
            logger.info("Added assign_courier_job to scheduler")

            scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Error adding jobs to scheduler: {e}")
            raise