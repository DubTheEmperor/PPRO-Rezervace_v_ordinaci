"""Export měsíčního výkazu do CSV (pro Excel v české lokalizaci).

Oddělovač `;` a kódování UTF-8 s BOM, aby Excel správně rozpoznal sloupce i diakritiku.
Nahoře je plochý seznam vykázaných výkonů (jeden řádek = jeden výkon návštěvy),
pod ním mezisoučty po pojišťovnách, celkový součet a identifikace výkazu.
"""
import csv
import io
from src.business.reports import MonthlyReport
from src.presentation.exports.formatting import fmt_date, fmt_datetime, unfinished_label

HEADER = [
    "Pojišťovna", "Datum", "Příjmení", "Jméno", "Rok narození", "Číslo pojištěnce",
    "Kód výkonu", "Název výkonu", "Počet", "Body/ks", "Body celkem",
]


def monthly_report_csv(report: MonthlyReport) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(HEADER)
    for section in report.sections:
        for visit in section.visits:
            for item in visit.items:
                writer.writerow([
                    section.code, fmt_date(visit.start_at), visit.patient_last_name,
                    visit.patient_first_name, visit.patient_birth_year, visit.insurance_number,
                    item.code, item.name, item.quantity, item.points_per_unit, item.total_points,
                ])

    writer.writerow([])
    writer.writerow(["Souhrn", "Název pojišťovny", "Návštěv", "Výkonů", "Body celkem"])
    for section in report.sections:
        writer.writerow([
            f"Mezisoučet {section.code}", section.name, section.visit_count,
            section.item_count, section.total_points,
        ])
    writer.writerow(["Celkem", report.insurance_label, report.visit_count, report.item_count, report.total_points])

    writer.writerow([])
    writer.writerow(["Ordinace", report.practice.name])
    writer.writerow(["IČZ", report.practice.icz])
    writer.writerow(["Lékař", report.doctor.full_name])
    writer.writerow(["IČP", report.doctor.icp or ""])
    writer.writerow(["Odbornost", report.doctor.specialty_code or ""])
    writer.writerow(["Období", report.period_label])
    writer.writerow(["Vygenerováno", fmt_datetime(report.generated_at), report.generated_by])
    if not report.period_complete:
        writer.writerow(["Upozornění", "Období ještě neskončilo – výkaz není konečný."])
    for item in report.unfinished:
        writer.writerow([
            "Neuzavřeno", fmt_datetime(item.start_at), item.patient_name, unfinished_label(item.state),
        ])

    return ("﻿" + buffer.getvalue()).encode("utf-8")
