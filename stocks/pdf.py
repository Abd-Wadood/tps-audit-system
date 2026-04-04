from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from django.utils import timezone

from .accounting import SECTION_CONFIG


def _format_revision_line(record):
    if getattr(record, "revision_count", 0) <= 0 or not getattr(record, "last_updated_by", None) or not getattr(record, "updated_at", None):
        return None

    updated_at = timezone.localtime(record.updated_at)
    updated_by = record.last_updated_by.get_full_name() or record.last_updated_by.username
    return f"This form was updated again by {updated_by} on {updated_at:%Y-%m-%d %I:%M %p}."


def _build_daily_stock_pdf(daily_stock, entries, totals, buffer):
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=10 * mm,
        leftMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    subtitle_style = ParagraphStyle(
        "StockSubtitle",
        parent=styles["BodyText"],
        textColor=colors.HexColor("#556678"),
        fontSize=10,
        spaceAfter=4,
    )

    rows = [[
        "No",
        "Item Name",
        "Opening",
        "Received",
        "Stock",
        "Sale",
        "Cancelled",
        "Exchange",
        "Ready",
        "InHand Stock",
        "Remaining",
        "Diff (-)",
        "Diff (+)",
    ]]

    for index, entry in enumerate(entries, start=1):
        pdf_in_hand = entry.stock - entry.sale + entry.cancelled
        pdf_diff_plus = max(pdf_in_hand - entry.remaining, 0)
        pdf_diff_minus = max(entry.remaining - pdf_in_hand, 0)
        rows.append(
            [
                str(index),
                entry.item.name,
                str(entry.opening),
                str(entry.received),
                str(entry.stock),
                str(entry.sale),
                str(entry.cancelled),
                str(entry.exchange),
                str(entry.ready),
                str(pdf_in_hand),
                str(entry.remaining),
                str(pdf_diff_plus),
                str(pdf_diff_minus),
            ]
        )

    rows.append(
        [
            "",
            "Totals",
            "",
            "",
            "",
            str(totals["total_orders"]),
            "",
            "",
            str(totals["shop_orders"]),
            "",
            "",
            "",
            "",
        ]
    )

    summary_rows = [
        ["Total Orders", str(totals["total_orders"])],
        ["Shop Orders", str(totals["shop_orders"])],
        ["Food Panda Orders", str(totals["food_panda_orders"])],
    ]

    story = [
        Paragraph("Daily Stock Control System", styles["Title"]),
        Paragraph(f"Branch: {daily_stock.branch.name}", subtitle_style),
        Paragraph(f"Date: {daily_stock.date:%Y-%m-%d}", subtitle_style),
    ]
    revision_line = _format_revision_line(daily_stock)
    if revision_line:
        story.append(Paragraph(revision_line, subtitle_style))
    story.append(Spacer(1, 6))

    table = Table(
        rows,
        colWidths=[12 * mm, 42 * mm, 16 * mm, 16 * mm, 16 * mm, 16 * mm, 18 * mm, 16 * mm, 16 * mm, 18 * mm, 16 * mm, 16 * mm, 20 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8dee7")),
                ("BACKGROUND", (0, 1), (-1, -2), colors.HexColor("#f8fbfd")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#edf3f8")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("LEFTPADDING", (1, 0), (1, -1), 6),
            ]
        )
    )

    summary_table = Table(summary_rows, colWidths=[55 * mm, 28 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6efe7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8dee7")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )

    story.extend([table, Spacer(1, 8), summary_table])
    document.build(story)


def _build_account_summary_pdf(sheet, buffer):
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Account Summary: {sheet.title}", styles["Title"]),
        Spacer(1, 8),
        Paragraph(f"Reference: {sheet.reference_number}", styles["BodyText"]),
        Paragraph(f"Date: {sheet.sheet_date:%Y-%m-%d}", styles["BodyText"]),
        Paragraph(f"Branch: {sheet.branch.name if sheet.branch else 'Unassigned'}", styles["BodyText"]),
        Paragraph(f"Prepared by: {sheet.created_by.get_full_name() or sheet.created_by.username}", styles["BodyText"]),
        Paragraph(f"System Sale: {sheet.system_sale:.2f}", styles["BodyText"]),
    ]
    revision_line = _format_revision_line(sheet)
    if revision_line:
        story.append(Paragraph(revision_line, styles["BodyText"]))
    story.append(Spacer(1, 12))

    for section_key, config in SECTION_CONFIG.items():
        section_data = getattr(sheet, f"{section_key}_purchases", None) if section_key in {"local", "market"} else None
        if section_key == "counter":
            section_data = sheet.counter_summary
        if section_key == "total":
            section_data = sheet.total_summary

        rows = [["Field", "Amount"]]
        values = section_data.get("values", {})
        for field_key, label in config["fields"]:
            rows.append([label, f"{values.get(field_key, '0')}"])
        for row in section_data.get("custom_rows", []):
            rows.append([row.get("label", "Custom"), row.get("value", "0")])
        rows.append([config["total_label"], sheet.totals.get(config["total_key"], "0")])

        story.append(Paragraph(config["title"], styles["Heading2"]))
        table = Table(rows, colWidths=[110 * mm, 45 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c4cfdb")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e6eef5")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ]
            )
        )
        story.extend([table, Spacer(1, 10)])

    summary_rows = [
        ["System Sale", sheet.totals.get("system_sale", "0")],
        ["Counter Sale", sheet.totals.get("counter_sale", "0")],
        ["Total Sale", sheet.totals.get("total_sale", "0")],
        ["Total Purchase", sheet.totals.get("total_purchase", "0")],
        ["Difference", sheet.totals.get("difference", "0")],
        ["Balance", sheet.totals.get("balance", "0")],
    ]
    summary_table = Table([["Account Summary", "Amount"]] + summary_rows, colWidths=[110 * mm, 45 * mm], repeatRows=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c4cfdb")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f7d9cb")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ]
        )
    )
    story.extend([Paragraph("ACCOUNT SUMMARY", styles["Heading2"]), summary_table])

    document.build(story)


def build_stock_sheet_pdf(*args):
    if len(args) == 2:
        sheet, buffer = args
        return _build_account_summary_pdf(sheet, buffer)

    if len(args) == 4:
        daily_stock, entries, totals, buffer = args
        return _build_daily_stock_pdf(daily_stock, entries, totals, buffer)

    raise TypeError("build_stock_sheet_pdf expected either 2 or 4 arguments")
