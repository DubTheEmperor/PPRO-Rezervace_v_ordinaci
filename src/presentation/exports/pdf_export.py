"""Export měsíčního výkazu do PDF (A4 na výšku) knihovnou fpdf2.

Rozvržení odpovídá běžnému ordinačnímu výkazu: hlavička s identifikací ordinace
a lékaře, oddíl pro každou pojišťovnu s mezisoučtem, souhrn podle kódů výkonů,
celkový součet bodů, upozornění na neuzavřené návštěvy a místo pro razítko a podpis.
Font DejaVu Sans Condensed je přibalen kvůli české diakritice (licence v adresáři fonts).
"""
from pathlib import Path
from fpdf import FPDF
from fpdf.fonts import FontFace
from src.business.reports import MonthlyReport
from src.presentation.exports.formatting import (
    fmt_date,
    fmt_datetime,
    fmt_points,
    items_label,
    patients_label,
    unfinished_label,
    visits_label,
)

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT = "DejaVu"

MARGIN = 12
# Datum | Pacient | Č. pojištěnce | Kód | Výkon | Počet | Body/ks | Body  (součet = 186 mm)
DETAIL_WIDTHS = (17, 36, 22, 11, 58, 11, 16, 15)
DETAIL_ALIGN = ("LEFT", "LEFT", "LEFT", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT")
SUMMARY_WIDTHS = (18, 118, 20, 30)
SUMMARY_ALIGN = ("LEFT", "LEFT", "RIGHT", "RIGHT")

HEADING_FILL = (226, 232, 240)
SECTION_FILL = (241, 245, 249)
TEXT_MUTED = (100, 116, 139)
WARNING_FILL = (254, 243, 199)


class _ReportPDF(FPDF):
    def __init__(self, report: MonthlyReport):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report = report
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=16)
        self.add_font(FONT, "", str(FONT_DIR / "DejaVuSansCondensed.ttf"))
        self.add_font(FONT, "B", str(FONT_DIR / "DejaVuSansCondensed-Bold.ttf"))
        self.set_title(f"Měsíční výkaz výkonů {report.period_label} – {report.doctor.full_name}")
        self.set_author(report.practice.name)
        self.set_creator("Ordinace Na Vyhlídce – rezervační systém")

    def footer(self):
        self.set_y(-12)
        self.set_font(FONT, "", 7.5)
        self.set_text_color(*TEXT_MUTED)
        r = self.report
        self.cell(0, 5, f"{r.practice.name} · {r.doctor.full_name} · výkaz {r.period_label}", align="L")
        self.set_x(MARGIN)
        self.cell(0, 5, f"Strana {self.page_no()}/{{nb}}", align="R")
        self.set_text_color(0, 0, 0)


def _header(pdf: _ReportPDF, r: MonthlyReport) -> None:
    pdf.set_font(FONT, "B", 15)
    pdf.cell(0, 8, "MĚSÍČNÍ VÝKAZ PROVEDENÝCH VÝKONŮ", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 5, f"Ambulantní péče · období {r.period_label} · {r.insurance_label}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    doctor = r.doctor
    left = [
        ("Poskytovatel", r.practice.name),
        ("Adresa", r.practice.address),
        ("IČZ", r.practice.icz),
    ]
    right = [
        ("Lékař", doctor.full_name),
        ("Odbornost", " – ".join(x for x in (doctor.specialty_code, doctor.specialization) if x) or "—"),
        ("IČP", doctor.icp or "—"),
    ]
    y0 = pdf.get_y()
    pdf.set_draw_color(203, 213, 225)
    pdf.rect(MARGIN, y0, 186, 3 * 5.5 + 3)
    for column, (x, rows) in enumerate(((MARGIN + 2, left), (MARGIN + 95, right))):
        pdf.set_xy(x, y0 + 1.5)
        for label, value in rows:
            pdf.set_x(x)
            pdf.set_font(FONT, "", 8)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.cell(22, 5.5, label)
            pdf.set_font(FONT, "B" if label in ("Poskytovatel", "Lékař") else "", 9)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(66, 5.5, value, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y0 + 3 * 5.5 + 5)

    pdf.set_font(FONT, "", 8)
    pdf.set_text_color(*TEXT_MUTED)
    status = "" if r.period_complete else " · období ještě neskončilo – výkaz není konečný"
    pdf.cell(0, 4.5, f"Vygenerováno {fmt_datetime(r.generated_at)} ({r.generated_by}){status}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


def _section_title(pdf: _ReportPDF, text: str) -> None:
    if pdf.will_page_break(22):
        pdf.add_page()
    pdf.set_font(FONT, "B", 10.5)
    pdf.set_fill_color(*SECTION_FILL)
    pdf.cell(0, 7, f"  {text}", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _detail_table(pdf: _ReportPDF, section) -> None:
    pdf.set_font(FONT, "", 8)
    headings = FontFace(emphasis="BOLD", fill_color=HEADING_FILL)
    with pdf.table(
        col_widths=DETAIL_WIDTHS, text_align=DETAIL_ALIGN, headings_style=headings,
        borders_layout="HORIZONTAL_LINES", line_height=4.6, padding=(0.8, 1.2),
        width=sum(DETAIL_WIDTHS), align="LEFT",
    ) as table:
        table.row(["Datum", "Pacient", "Č. pojištěnce", "Kód", "Výkon", "Počet", "Body/ks", "Body"])
        for visit in section.visits:
            for index, item in enumerate(visit.items):
                first = index == 0
                table.row([
                    fmt_date(visit.start_at) if first else "",
                    f"{visit.patient_name} ({visit.patient_birth_year})" if first else "",
                    visit.insurance_number if first else "",
                    item.code,
                    item.name,
                    str(item.quantity),
                    fmt_points(item.points_per_unit),
                    fmt_points(item.total_points),
                ])
        bold = FontFace(emphasis="BOLD", fill_color=SECTION_FILL)
        row = table.row(style=bold)
        row.cell(
            f"Mezisoučet {section.code} {section.short_name}: {visits_label(section.visit_count)}, "
            f"{patients_label(section.patient_count)}",
            colspan=5,
        )
        row.cell(str(section.item_count))
        row.cell("")
        row.cell(fmt_points(section.total_points))
    pdf.ln(4)


def _summary_table(pdf: _ReportPDF, r: MonthlyReport) -> None:
    _section_title(pdf, "Souhrn podle kódů výkonů")
    pdf.set_font(FONT, "", 8.5)
    headings = FontFace(emphasis="BOLD", fill_color=HEADING_FILL)
    with pdf.table(
        col_widths=SUMMARY_WIDTHS, text_align=SUMMARY_ALIGN, headings_style=headings,
        borders_layout="HORIZONTAL_LINES", line_height=4.8, padding=(0.8, 1.2),
        width=sum(SUMMARY_WIDTHS), align="LEFT",
    ) as table:
        table.row(["Kód", "Název výkonu", "Počet", "Body"])
        for item in r.procedure_summary:
            table.row([item.code, item.name, str(item.quantity), fmt_points(item.total_points)])
    pdf.ln(3)


def _totals(pdf: _ReportPDF, r: MonthlyReport) -> None:
    if pdf.will_page_break(14):
        pdf.add_page()
    pdf.set_draw_color(15, 23, 42)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(MARGIN, y, MARGIN + 186, y)
    pdf.ln(1.5)
    pdf.set_font(FONT, "", 9)
    pdf.cell(120, 7, f"Celkem: {visits_label(r.visit_count)} · {patients_label(r.patient_count)} · "
                     f"{items_label(r.item_count)}")
    pdf.set_font(FONT, "B", 12)
    pdf.cell(66, 7, f"CELKEM BODŮ: {fmt_points(r.total_points)}", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_line_width(0.2)
    pdf.ln(3)


def _warnings(pdf: _ReportPDF, r: MonthlyReport) -> None:
    if not r.unfinished:
        return
    lines = [
        f"{fmt_datetime(item.start_at)}  {item.patient_name} – {unfinished_label(item.state)}"
        for item in r.unfinished
    ]
    if pdf.will_page_break(10 + 4.5 * len(lines)):
        pdf.add_page()
    pdf.set_fill_color(*WARNING_FILL)
    pdf.set_font(FONT, "B", 9)
    pdf.multi_cell(
        0, 5.5,
        f"Upozornění: neuzavřené návštěvy v období ({len(r.unfinished)}) ve výkazu chybí – "
        "výkaz není úplný.",
        fill=True, new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font(FONT, "", 8.5)
    pdf.multi_cell(0, 4.5, "\n".join(lines), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _signature(pdf: _ReportPDF) -> None:
    if pdf.will_page_break(24):
        pdf.add_page()
    pdf.ln(10)
    pdf.set_font(FONT, "", 8.5)
    x = MARGIN + 110
    y = pdf.get_y()
    pdf.set_draw_color(100, 116, 139)
    pdf.line(x, y, x + 76, y)
    pdf.set_xy(x, y + 1)
    pdf.cell(76, 5, "Razítko a podpis lékaře", align="C")


def monthly_report_pdf(report: MonthlyReport) -> bytes:
    pdf = _ReportPDF(report)
    pdf.add_page()
    _header(pdf, report)

    if not report.sections:
        pdf.set_font(FONT, "", 10)
        pdf.cell(0, 10, "V tomto období nejsou žádné uzavřené návštěvy.", new_x="LMARGIN", new_y="NEXT")
    for section in report.sections:
        _section_title(pdf, f"Pojišťovna {section.code} – {section.name}")
        _detail_table(pdf, section)
    if report.procedure_summary:
        _summary_table(pdf, report)
    _totals(pdf, report)
    _warnings(pdf, report)
    _signature(pdf)
    return bytes(pdf.output())
