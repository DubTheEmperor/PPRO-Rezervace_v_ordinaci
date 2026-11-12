"""Unit testy čisté logiky měsíčního výkazu (FP7) a navazujících úprav bez HTTP."""
from datetime import date, datetime
import pytest
from pydantic import ValidationError
from src.business import reports
from src.business.dto import DoctorCreate
from src.business.exceptions import BusinessRuleError
from src.business.seed import seed_demo_report_visits, seed_initial_patients
from src.infrastructure.models.visit_model import VisitModel, VisitStatus
from src.presentation.exports.formatting import fmt_points, report_filename, visits_label


def visit(visit_id, day, insurance, patient_id, items):
    return reports.ReportVisit(
        visit_id=visit_id, start_at=datetime(2026, 10, day, 9, 0), patient_id=patient_id,
        patient_first_name="Jan", patient_last_name=f"Pacient{patient_id}", patient_birth_year=1980,
        insurance_number=f"80010{patient_id}1234", insurance_code=insurance,
        items=tuple(reports.ReportItem(code, f"Výkon {code}", qty, pts) for code, qty, pts in items),
    )


def build(visits, unfinished=(), now=datetime(2026, 11, 12, 10, 0)):
    return reports.build_monthly_report(
        practice=reports.PracticeInfo("Ordinace", "Adresa", "52999000"),
        doctor=reports.DoctorInfo(1, "MUDr. Jana Hrubá", None, "52999101", "001"),
        year=2026, month=10, insurance_code=None, visits=visits, unfinished=unfinished,
        now=now, generated_by="Recepce",
    )


@pytest.mark.parametrize("value, expected", [("2026-10", (2026, 10)), (" 2026-01 ", (2026, 1))])
def test_parse_month(value, expected):
    assert reports.parse_month(value) == expected


@pytest.mark.parametrize("value", ["2026-00", "2026-13", "1999-05", "26-10", "", None])
def test_parse_month_invalid(value):
    with pytest.raises(BusinessRuleError):
        reports.parse_month(value)


def test_month_bounds_including_december():
    assert reports.month_bounds(2026, 2) == (datetime(2026, 2, 1), datetime(2026, 3, 1))
    assert reports.month_bounds(2026, 12) == (datetime(2026, 12, 1), datetime(2027, 1, 1))


def test_ensure_not_future():
    reports.ensure_not_future(2026, 11, date(2026, 11, 1))
    reports.ensure_not_future(2025, 12, date(2026, 1, 15))
    with pytest.raises(BusinessRuleError):
        reports.ensure_not_future(2026, 12, date(2026, 11, 30))


def test_build_groups_sections_and_summarizes():
    report = build([
        visit(3, 20, "207", 3, [("01023", 1, 130)]),
        visit(2, 15, "111", 2, [("01021", 1, 520), ("09215", 3, 16)]),
        visit(1, 5, "111", 1, [("09215", 2, 16)]),
    ])
    assert [s.code for s in report.sections] == ["111", "207"]
    vzp = report.sections[0]
    assert [v.visit_id for v in vzp.visits] == [1, 2]          # chronologicky
    assert (vzp.visit_count, vzp.patient_count, vzp.item_count, vzp.total_points) == (2, 2, 6, 600)
    assert report.total_points == 730
    assert report.item_count == 7
    summary = {s.code: (s.quantity, s.total_points) for s in report.procedure_summary}
    assert summary == {"01021": (1, 520), "01023": (1, 130), "09215": (5, 80)}
    assert report.period_complete is True
    assert report.period_label == "10/2026"


def test_build_empty_report_and_incomplete_period():
    report = build([], now=datetime(2026, 10, 20, 12, 0))
    assert report.sections == () and report.total_points == 0
    assert report.period_complete is False


def test_formatting_helpers():
    assert fmt_points(1047) == "1 047"
    assert [visits_label(n) for n in (1, 3, 5)] == ["1 návštěva", "3 návštěvy", "5 návštěv"]
    assert report_filename(build([]), "pdf") == "vykaz_hruba_2026-10.pdf"


@pytest.mark.parametrize("field, value", [("icp", "1234567"), ("icp", "abcdefgh"), ("specialty_code", "01")])
def test_doctor_billing_identifiers_validation(field, value):
    with pytest.raises(ValidationError):
        DoctorCreate(full_name="MUDr. Test", **{field: value})
    assert DoctorCreate(full_name="MUDr. Test", icp="12345678", specialty_code="001").icp == "12345678"


def test_seed_demo_report_visits_is_idempotent(db_session):
    seed_initial_patients(db_session)
    seed_demo_report_visits(db_session)
    closed = db_session.query(VisitModel).filter(VisitModel.status == VisitStatus.CLOSED).count()
    assert closed > 0
    seed_demo_report_visits(db_session)
    assert db_session.query(VisitModel).filter(VisitModel.status == VisitStatus.CLOSED).count() == closed
