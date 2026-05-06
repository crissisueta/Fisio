from datetime import date, datetime, time

from django.utils import timezone


def ensure_aware_datetime(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def combine_date_time(value_date: date, value_time: time) -> datetime:
    return datetime.combine(value_date, value_time)


def duration_minutes_for_times(start_time: time, end_time: time) -> int:
    return int(
        (
            datetime.combine(datetime.today(), end_time)
            - datetime.combine(datetime.today(), start_time)
        ).total_seconds()
        // 60
    )


def duration_minutes_for_datetime_end(start: datetime, end_time: time) -> int:
    return int(
        (
            datetime.combine(start.date(), end_time)
            - datetime.combine(start.date(), start.time())
        ).total_seconds()
        // 60
    )

