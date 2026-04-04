from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def generate_submission_receipt(
    output_path: Path,
    document_id: str,
    username: str,
    document_date: str,
    subject: str,
    status: str,
    timestamp: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    pdf.setTitle(f"Tanda Terima {document_id}")

    top = height - 25 * mm
    left = 20 * mm
    line_gap = 10 * mm

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(left, top, "Tanda Terima Pengajuan Dokumen")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, top - 8 * mm, f"Dibuat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    rows = [
        ("Document ID", document_id),
        ("User Name", username),
        ("Date", document_date),
        ("Subject", subject),
        ("Status", status),
        ("Timestamp", timestamp),
    ]

    y = top - 22 * mm
    pdf.setFont("Helvetica", 12)
    for label, value in rows:
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(left, y, f"{label}:")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(left + 38 * mm, y, value)
        y -= line_gap

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(left, y - 4 * mm, "Harap simpan tanda terima ini untuk arsip Anda.")

    pdf.showPage()
    pdf.save()

