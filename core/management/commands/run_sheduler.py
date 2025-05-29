from django.core.management.base import BaseCommand
import time
import logging
from core.tasks import assign_florist_task, assign_courier_task

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Запускает фоновый планировщик задач (назначение флористов и курьеров)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Фоновый планировщик запущен...'))
        try:
            while True:
                logger.info("🟢 Цикл планировщика начат")

                assign_florist_task()
                assign_courier_task()

                logger.info("⏳ Пауза перед следующим циклом...")
                time.sleep(60)  # Повторять каждые 60 секунд (можно настроить)

        except KeyboardInterrupt:
            logger.warning("⛔ Планировщик остановлен вручную")
            self.stdout.write(self.style.WARNING('Фоновый планировщик остановлен'))
