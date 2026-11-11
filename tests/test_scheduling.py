"""Unit testy čisté doménové logiky plánování (bez databáze)."""
from datetime import datetime, time
from src.business import scheduling

BLOCKS = [(time(8, 0), time(12, 0)), (time(13, 0), time(16, 0))]
DAY = datetime(2030, 1, 7)  # pondělí


def at(h: int, m: int = 0) -> datetime:
    return DAY.replace(hour=h, minute=m)


def test_is_aligned():
    assert scheduling.is_aligned(at(8, 0))
    assert scheduling.is_aligned(at(8, 45))
    assert not scheduling.is_aligned(at(8, 10))
    assert not scheduling.is_aligned(at(8, 0).replace(second=30))


def test_slot_starts_splits_interval_into_15_minute_slots():
    assert scheduling.slot_starts(at(8, 0), at(8, 45)) == [at(8, 0), at(8, 15), at(8, 30)]
    assert scheduling.slot_count(at(8, 0), at(9, 0)) == 4


def test_fits_inside_block():
    assert scheduling.fits_office_hours(BLOCKS, at(8, 0), at(8, 15))
    assert scheduling.fits_office_hours(BLOCKS, at(11, 30), at(12, 0))
    assert scheduling.fits_office_hours(BLOCKS, at(13, 0), at(16, 0))


def test_does_not_fit_across_lunch_break():
    assert not scheduling.fits_office_hours(BLOCKS, at(11, 45), at(12, 15))
    assert not scheduling.fits_office_hours(BLOCKS, at(11, 45), at(13, 15))


def test_does_not_fit_outside_hours():
    assert not scheduling.fits_office_hours(BLOCKS, at(7, 45), at(8, 15))
    assert not scheduling.fits_office_hours(BLOCKS, at(16, 0), at(16, 15))
    assert not scheduling.fits_office_hours([], at(9, 0), at(9, 15))


def test_validate_blocks_ok():
    assert scheduling.validate_blocks([(0, time(8, 0), time(12, 0)), (0, time(12, 0), time(14, 0))]) == []


def test_validate_blocks_detects_errors():
    assert scheduling.validate_blocks([(0, time(8, 10), time(12, 0))])  # nezarovnaný
    assert scheduling.validate_blocks([(0, time(12, 0), time(8, 0))])  # obrácený
    assert scheduling.validate_blocks([(0, time(8, 0), time(12, 0)), (0, time(11, 0), time(13, 0))])  # překryv
    assert scheduling.validate_blocks([(7, time(8, 0), time(9, 0))])  # neplatný den


# --- Volné termíny (FP6) -----------------------------------------------------------------------

EARLY = datetime(2029, 1, 1)  # „teď“ před zkoumaným dnem


def test_free_intervals_follow_office_hours_and_do_not_merge_over_lunch():
    result = scheduling.free_intervals(DAY.date(), BLOCKS, set(), EARLY)
    assert result == [(at(8), at(12)), (at(13), at(16))]


def test_taken_slot_splits_interval():
    taken = {at(9, 0), at(9, 15)}
    result = scheduling.free_intervals(DAY.date(), BLOCKS, taken, EARLY)
    assert result[:2] == [(at(8), at(9)), (at(9, 30), at(12))]


def test_past_slots_are_not_free():
    # 9:07 – rozběhnutý slot 9:00 už nabízet nelze, první volno je 9:15
    result = scheduling.free_intervals(DAY.date(), BLOCKS, set(), at(9, 7))
    assert result[0] == (at(9, 15), at(12))


def test_day_without_office_hours_has_no_free_slots():
    assert scheduling.free_intervals(DAY.date(), [], set(), EARLY) == []


def test_first_free_start_needs_contiguous_interval():
    intervals = [(at(8), at(8, 15)), (at(10), at(11))]
    assert scheduling.first_free_start(intervals, 15) == (at(8), at(8, 15))
    assert scheduling.first_free_start(intervals, 30) == (at(10), at(10, 30))
    assert scheduling.first_free_start(intervals, 90) is None
