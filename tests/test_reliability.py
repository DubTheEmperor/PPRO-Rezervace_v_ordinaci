"""FP5 – unit testy doménové logiky spolehlivosti pacienta (bez databáze)."""
from datetime import datetime, timedelta, timezone
import pytest
from src.business import reliability as rel


@pytest.mark.parametrize(
    "score, level",
    [(0, rel.LEVEL_GREEN), (1, rel.LEVEL_GREEN), (2, rel.LEVEL_YELLOW), (3, rel.LEVEL_YELLOW),
     (4, rel.LEVEL_RED), (9, rel.LEVEL_RED)],
)
def test_level_thresholds(score, level):
    assert rel.level_for(score) == level


def test_window_start_is_twelve_months_back():
    assert rel.window_start(datetime(2026, 11, 11, 10, 30)) == datetime(2025, 11, 11, 10, 30)


def test_window_start_clamps_end_of_month():
    # 29. 2. 2028 → o 12 měsíců dříve neexistuje 29. 2. 2027
    assert rel.window_start(datetime(2028, 2, 29, 8, 0)) == datetime(2027, 2, 28, 8, 0)
    assert rel.window_start(datetime(2026, 3, 31), months=1) == datetime(2026, 2, 28)


def test_is_late_compares_utc_cancellation_with_local_start():
    start = datetime(2026, 11, 20, 9, 0)  # lokální čas (CET = UTC+1)
    # 23 h předem: 19. 11. 10:00 lokálně = 09:00 UTC
    assert rel.is_late(datetime(2026, 11, 19, 9, 0, tzinfo=timezone.utc), start)
    # 25 h předem: 19. 11. 08:00 lokálně = 07:00 UTC
    assert not rel.is_late(datetime(2026, 11, 19, 7, 0, tzinfo=timezone.utc), start)
    assert not rel.is_late(None, start)


def test_evaluate_counts_cancellations_and_no_shows_equally():
    start = datetime(2026, 11, 20, 9, 0)
    events = [
        (rel.EVENT_CANCELLED, start, datetime(2026, 11, 10, tzinfo=timezone.utc)),
        (rel.EVENT_CANCELLED, start, start - timedelta(hours=2)),  # pozdní zrušení
        (rel.EVENT_NO_SHOW, start, None),
    ]
    result = rel.evaluate(events)
    assert (result.cancelled, result.no_show, result.late) == (2, 1, 1)
    # Pozdní zrušení na skóre vliv nemá – váha 1:1
    assert result.score == 3
    assert result.level == rel.LEVEL_YELLOW


def test_evaluate_empty_is_green():
    result = rel.evaluate([])
    assert result.score == 0 and result.level == rel.LEVEL_GREEN
