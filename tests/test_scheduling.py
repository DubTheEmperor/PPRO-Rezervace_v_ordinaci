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
