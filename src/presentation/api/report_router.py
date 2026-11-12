from typing import Literal, Optional
from urllib.parse import quote
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from src.business.domain import get_db, User
from src.business.services.report_service import ReportService
from src.presentation.dependencies import get_current_user
from src.presentation.exports.csv_export import monthly_report_csv
from src.presentation.exports.formatting import report_filename
from src.presentation.exports.pdf_export import monthly_report_pdf
from src.presentation.schemas.report_schemas import MonthlyReportResponse

router = APIRouter(prefix="/reports", tags=["Výkazy pro pojišťovny"])

MonthQuery = Query(..., description="Kalendářní měsíc ve tvaru RRRR-MM", examples=["2026-10"])
InsuranceQuery = Query(None, description="Kód pojišťovny (prázdné = všechny pojišťovny)")

MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "pdf": "application/pdf",
}


@router.get(
    "/monthly",
    response_model=MonthlyReportResponse,
    summary="Měsíční výkaz výkonů lékaře",
    description=(
        "Uzavřené návštěvy lékaře v kalendářním měsíci členěné po pojišťovnách s mezisoučty, "
        "souhrnem podle kódů výkonů a celkovým součtem bodů. Obsahuje i seznam proběhlých, "
        "ale neuzavřených návštěv (výkaz není úplný). Recepce a administrátor – libovolný lékař, "
        "lékař – jen vlastní výkaz."
    ),
)
def get_monthly_report(
    doctor_id: int,
    month: str = MonthQuery,
    insurance_code: Optional[str] = InsuranceQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = ReportService(db).get_monthly_report(doctor_id, month, current_user, insurance_code)
    return MonthlyReportResponse.model_validate(report)


@router.get(
    "/monthly/export",
    summary="Stažení měsíčního výkazu (CSV / PDF)",
    description="Stejný výkaz jako `/reports/monthly` ke stažení jako CSV (Excel, `;`, UTF-8 s BOM) nebo PDF.",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}, "application/pdf": {}}}},
)
def export_monthly_report(
    doctor_id: int,
    month: str = MonthQuery,
    export_format: Literal["csv", "pdf"] = Query(..., alias="format", description="csv | pdf"),
    insurance_code: Optional[str] = InsuranceQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = ReportService(db).get_monthly_report(doctor_id, month, current_user, insurance_code)
    content = monthly_report_csv(report) if export_format == "csv" else monthly_report_pdf(report)
    filename = report_filename(report, export_format)
    return Response(
        content=content,
        media_type=MEDIA_TYPES[export_format],
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}",
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
