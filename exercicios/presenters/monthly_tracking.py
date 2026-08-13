from __future__ import annotations

from ..services.monthly_tracking import MonthlyExerciseRow, MonthlyExerciseTrackingTable


COLOR_CLASS_MAP = {
    "red": "text-danger fw-semibold",
    "blue": "text-primary fw-semibold",
    "black": "text-dark",
}
DAY_CLASS_MAP = {
    "past": "exercise-tracking-day-past",
    "today": "exercise-tracking-day-today",
    "future": "exercise-tracking-day-future",
}


def present_monthly_tracking_table(
    table: MonthlyExerciseTrackingTable,
    next_table: MonthlyExerciseTrackingTable | None = None,
) -> dict:
    next_rows_by_exercise = _rows_by_exercise_id(next_table) if next_table else {}

    return {
        "patient_id": table.patient_id,
        "month": table.month,
        "month_param": table.month_param,
        "month_label": table.month_label,
        "previous_month_param": table.previous_month_param,
        "next_month_param": table.next_month_param,
        "next_month_label": next_table.month_label if next_table else None,
        "days": [_present_day(day) for day in table.days],
        "next_month_days": [_present_day(day) for day in next_table.days] if next_table else [],
        "last_session_id": table.last_session_id,
        "groups": [
            {
                "category_id": group.category_id,
                "category": group.category_name,
                "category_color": group.category_color,
                "exercises": [
                    {
                        "exercise_id": exercise.exercise_id,
                        "name": exercise.name,
                        "name_class": get_color_class(exercise.color_state),
                        "color_state": exercise.color_state,
                        "last_performed": exercise.last_performed,
                        "performed_in_last_session": exercise.performed_in_last_session,
                        "days": [_present_exercise_day(day) for day in exercise.days],
                        "next_month_days": _present_next_month_days(
                            next_rows_by_exercise.get(exercise.exercise_id),
                            next_table,
                        ),
                    }
                    for exercise in group.exercises
                ],
            }
            for group in table.groups
        ],
    }


def _rows_by_exercise_id(table: MonthlyExerciseTrackingTable | None) -> dict[int, MonthlyExerciseRow]:
    if table is None:
        return {}

    return {
        exercise.exercise_id: exercise
        for group in table.groups
        for exercise in group.exercises
    }


def _present_day(day) -> dict:
    return {
        "day": day.day,
        "date": day.date,
        "temporal_state": day.temporal_state,
        "header_class": get_day_class(day.temporal_state),
    }


def _present_exercise_day(day) -> dict:
    return {
        "day": day.day,
        "date": day.date,
        "marked": day.marked,
        "performed": day.performed,
        "temporal_state": day.temporal_state,
        "cell_class": get_day_class(day.temporal_state),
    }


def _present_next_month_days(
    row: MonthlyExerciseRow | None,
    next_table: MonthlyExerciseTrackingTable | None,
) -> list[dict]:
    if row is not None:
        return [_present_exercise_day(day) for day in row.days]
    if next_table is None:
        return []

    return [
        {
            "day": day.day,
            "date": day.date,
            "marked": False,
            "performed": False,
            "temporal_state": day.temporal_state,
            "cell_class": get_day_class(day.temporal_state),
        }
        for day in next_table.days
    ]


def get_color_class(color_state: str) -> str:
    return COLOR_CLASS_MAP.get(color_state, COLOR_CLASS_MAP["black"])


def get_day_class(temporal_state: str) -> str:
    return DAY_CLASS_MAP.get(temporal_state, DAY_CLASS_MAP["future"])


__all__ = [
    "COLOR_CLASS_MAP",
    "DAY_CLASS_MAP",
    "get_color_class",
    "get_day_class",
    "present_monthly_tracking_table",
]
