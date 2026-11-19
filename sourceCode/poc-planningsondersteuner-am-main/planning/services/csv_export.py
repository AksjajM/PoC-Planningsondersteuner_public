"""Services for exporting saved weekly planning data as CSV rows."""

from .weekly_planning import build_readonly_weekly_planning, get_planning_employees

CSV_HEADERS = [
    "Employee",
    "Year",
    "ISO week",
    "Date",
    "Day",
    "Part of day",
    "Planned role",
]


def build_weekly_planning_csv_rows(year, week_number):
    """Builds CSV rows for saved planning, including N/A for empty time slots."""
    _week_dates, planning_rows = build_readonly_weekly_planning(
        year,
        week_number,
        get_planning_employees(),
    )
    rows = []
    for planning_row in planning_rows:
        for cell in planning_row["cells"]:
            rows.append(
                [
                    planning_row["user"].username,
                    year,
                    week_number,
                    cell["date"].isoformat(),
                    cell["date"].strftime("%A"),
                    cell["part_of_day"].title(),
                    cell["role"].name if cell["role"] is not None else "N/A",
                ]
            )
    return rows
