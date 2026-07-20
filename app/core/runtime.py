from time import monotonic

START_TIME = monotonic()


def get_uptime_seconds() -> int:
    return int(monotonic() - START_TIME)