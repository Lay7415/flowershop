# core/tasks.py
import logging
import random
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Count, Q

# Важно: Используйте правильный путь для импорта ваших моделей
# Если models.py в другом приложении, импортируйте оттуда
try:
    from users.models import User
    from orders.models import Order
except ImportError:
    # Логируем ошибку, если модели не найдены, но не прерываем работу планировщика
    # (он может запуститься до того, как все приложения готовы)
    logging.error(
        "Не удалось импортировать модели User или Order в core.tasks. Возможно, приложения еще не загружены."
    )
    # Можно определить заглушки или вернуть None, чтобы задачи не падали при старте
    User = None
    Order = None


logger = logging.getLogger(__name__)  # Используйте имя логгера из настроек


def assign_florist_task():
    """
    Находит оплаченные заказы без флориста и назначает свободного флориста.
    Назначает заказы, до времени доставки которых осталось 80-210 минут
    (чтобы учесть разницу во времени между временем создания заказа и временем доставки).
    """
    logger.info("=== Начало выполнения assign_florist_task ===")

    # Проверяем, загрузились ли модели
    if not User or not Order:
        logger.warning(
            "Модели User/Order не загружены, пропуск задачи assign_florist_task."
        )
        return

    # Вычисляем временное окно для назначения
    current_time = timezone.now()
    min_threshold = current_time + timedelta(minutes=30)
    max_threshold = current_time + timedelta(
        minutes=210
    )  # Увеличиваем окно для учета разницы во времени

    # Ищем заказы, которые:
    # 1. Оплачены
    # 2. Без флориста
    # 3. Время доставки в пределах 80-210 минут от текущего времени
    orders_to_assign = Order.objects.filter(
        status="paid",
        florist__isnull=True,
        delivery_datetime__gte=min_threshold,
        delivery_datetime__lte=max_threshold,
    ).order_by("delivery_datetime")
    
    orders_count = orders_to_assign.count()
    logger.info(f"Найдено {orders_count} заказов для назначения флористам")
    logger.info(
        f"Текущее время: {current_time}, мин. порог: {min_threshold}, макс. порог: {max_threshold}"
    )

    # Отладочный вывод для каждого найденного заказа
    for order in orders_to_assign:
        logger.info(f"Заказ #{order.id}: время доставки {order.delivery_datetime}")

    if not orders_count:
        logger.info("Нет заказов для назначения флористов.")
        return

    # Получаем список всех активных флористов
    florists = User.objects.filter(role="florist", is_active=True)
    florists_count = florists.count()
    logger.info(f"Найдено {florists_count} активных флористов")

    if not florists_count:
        logger.warning("Нет активных флористов в системе!")
        return

    # Находим флориста с наименьшим числом активных заказов
    florists_with_load = florists.annotate(
        active_orders_count=Count(
            "handled_orders", filter=Q(handled_orders__status="paid")
        )
    ).order_by("active_orders_count")

    logger.info("Начинаем распределение заказов между флористами...")
    florist_iterator = iter(florists_with_load)

    assigned_count = 0
    for order in orders_to_assign:
        try:
            selected_florist = next(florist_iterator)
            logger.debug(
                f"Выбран флорист {selected_florist.email} для заказа #{order.id}"
            )
        except StopIteration:
            if not florists_with_load:
                logger.error("Список флористов пуст, не могу назначить.")
                break
            logger.info("Перезапуск итератора флористов")
            florist_iterator = iter(florists_with_load)
            try:
                selected_florist = next(florist_iterator)
                logger.debug(
                    f"После перезапуска выбран флорист {selected_florist.email}"
                )
            except StopIteration:
                logger.error("Не удалось выбрать флориста после перезапуска итератора.")
                break

        try:
            order.florist = selected_florist
            order.save(update_fields=["florist", "updated_at"])
            assigned_count += 1
            logger.info(
                f"Заказ #{order.id} успешно назначен флористу {selected_florist.email}"
            )
        except Exception as e:
            logger.error(f"Ошибка при назначении заказа #{order.id}: {str(e)}")

    logger.info(
        f"=== Завершение assign_florist_task. Назначено заказов: {assigned_count} ==="
    )


def assign_courier_task():
    """
    Находит готовые к доставке заказы без курьера и назначает свободного курьера.
    """
    logger.info("=== Начало выполнения assign_courier_task ===")

    if not User or not Order:
        logger.warning(
            "Модели User/Order не загружены, пропуск задачи assign_courier_task."
        )
        return

    # Ищем заказы, готовые к доставке, без курьера
    orders_to_assign = Order.objects.filter(
        status="ready", courier__isnull=True
    ).order_by("updated_at")

    orders_count = orders_to_assign.count()
    logger.info(f"Найдено {orders_count} заказов для назначения курьерам")

    if not orders_count:
        logger.info("Нет заказов для назначения курьерам.")
        return

    # Получаем список активных курьеров
    couriers = User.objects.filter(role="courier", is_active=True)
    couriers_count = couriers.count()
    logger.info(f"Найдено {couriers_count} активных курьеров")

    if not couriers_count:
        logger.warning("Нет активных курьеров в системе!")
        return

    # Ищем курьера с наименьшей нагрузкой
    couriers_with_load = couriers.annotate(
        active_deliveries_count=Count(
            "delivered_orders",
            filter=Q(delivered_orders__status__in=["ready", "delivering"]),
        )
    ).order_by("active_deliveries_count")

    logger.info("Начинаем распределение заказов между курьерами...")
    courier_iterator = iter(couriers_with_load)
    assigned_count = 0

    for order in orders_to_assign:
        try:
            selected_courier = next(courier_iterator)
            logger.debug(
                f"Выбран курьер {selected_courier.email} для заказа #{order.id}"
            )
        except StopIteration:
            if not couriers_with_load:
                logger.error("Список курьеров пуст, не могу назначить.")
                break
            logger.info("Перезапуск итератора курьеров")
            courier_iterator = iter(couriers_with_load)
            try:
                selected_courier = next(courier_iterator)
                logger.debug(
                    f"После перезапуска выбран курьер {selected_courier.email}"
                )
            except StopIteration:
                logger.error("Не удалось выбрать курьера после перезапуска итератора.")
                break

        try:
            order.courier = selected_courier
            order.save(update_fields=["courier", "updated_at"])
            assigned_count += 1
            logger.info(
                f"Заказ #{order.id} успешно назначен курьеру {selected_courier.email}"
            )
        except Exception as e:
            logger.error(f"Ошибка при назначении заказа #{order.id}: {str(e)}")

    logger.info(
        f"=== Завершение assign_courier_task. Назначено заказов: {assigned_count} ==="
    )
