"""Business day and timeline calculations for ZentroMart VoiceOps.

Calculates refund arrival windows and return deadlines according to policy:
- Reference date: 20 October 2026
- Business days: Monday to Saturday, skipping Sundays and holidays in holidays.csv
- Return windows: Calendar days from delivery date
"""
import csv
from datetime import datetime, date, timedelta
from typing import List, Tuple, Optional, Set

from .config import DATA_DIR, REFERENCE_DATE


def load_holidays() -> Set[date]:
    """Load warehouse closure holiday dates from data/holidays.csv."""
    holidays = set()
    holidays_file = DATA_DIR / "holidays.csv"
    if holidays_file.exists():
        with open(holidays_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d_str = row.get("date", "").strip()
                if d_str:
                    try:
                        holidays.add(datetime.strptime(d_str, "%Y-%m-%d").date())
                    except ValueError:
                        pass
    else:
        # Default known holidays from KB-00.3
        for d_str in ["2026-08-15", "2026-10-02", "2026-10-19", "2026-11-09"]:
            holidays.add(datetime.strptime(d_str, "%Y-%m-%d").date())
    return holidays


HOLIDAYS = load_holidays()


def is_business_day(d: date) -> bool:
    """Check if a date is a business day (Monday to Saturday, excluding holidays)."""
    # weekday: 0=Mon, 1=Tue, ..., 5=Sat, 6=Sun
    if d.weekday() == 6:  # Sunday
        return False
    if d in HOLIDAYS:
        return False
    return True


def add_business_days(start_date: date, n_days: int) -> date:
    """Add n business days to start_date, skipping Sundays and holidays."""
    cur = start_date
    added = 0
    while added < n_days:
        cur += timedelta(days=1)
        if is_business_day(cur):
            added += 1
    return cur


def compute_refund_window(start_date_str: str, method: str) -> Tuple[str, str, str]:
    """Compute exact refund arrival dates based on payment method and business days.

    Returns: (min_date_str, max_date_str, spoken_phrase)
    """
    try:
        dt = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return "", "", ""

    m_lower = method.lower()
    if "wallet" in m_lower:
        return "Instant", "Within 2 hours", "instant, within 2 hours of approval"

    if "upi" in m_lower:
        min_d = add_business_days(dt, 1)
        max_d = add_business_days(dt, 3)
    elif "net" in m_lower:
        min_d = add_business_days(dt, 3)
        max_d = add_business_days(dt, 5)
    elif "card" in m_lower or "credit" in m_lower or "debit" in m_lower:
        min_d = add_business_days(dt, 5)
        max_d = add_business_days(dt, 7)
    else:
        min_d = add_business_days(dt, 3)
        max_d = add_business_days(dt, 5)

    max_spoken = max_d.strftime("%d %B %Y").lstrip("0")
    min_spoken = min_d.strftime("%d %B %Y").lstrip("0")
    phrase = f"Between {min_spoken} and {max_spoken} ({max_d.isoformat()} / {max_spoken})"
    return min_d.isoformat(), max_d.isoformat(), phrase
