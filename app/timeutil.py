"""All datetimes in this app are naive UTC. SQLite (the default backend)
drops tzinfo on round-trip, so mixing tz-aware and naive datetimes would
crash comparisons the moment a value comes back from the DB. Standardizing
on naive-UTC everywhere avoids that regardless of which DB backend is used.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
