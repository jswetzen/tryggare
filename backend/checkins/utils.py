"""
Utility functions for check-in operations, including PDF label generation.
"""

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF


def generate_label_pdf(checkin_records):
    """
    Generate a PDF with labels for printing.

    Args:
        checkin_records: QuerySet of CheckInRecord objects

    Returns:
        bytes: PDF file content
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Label dimensions (2.5" x 1.5" labels, adjust based on actual Brother label size)
    label_width = 2.5 * inch
    label_height = 1.5 * inch
    margin = 0.5 * inch

    # Layout: 3 columns x 6 rows per page
    labels_per_row = 3
    labels_per_col = 6

    # Calculate x positions for 3 columns
    x_positions = [
        margin + i * (label_width + 0.25 * inch) for i in range(labels_per_row)
    ]
    # Calculate y positions for 6 rows (from top to bottom)
    y_positions = [
        height - margin - (i + 1) * (label_height + 0.25 * inch)
        for i in range(labels_per_col)
    ]

    label_count = 0

    for record in checkin_records:
        # Calculate position on current page
        row = label_count % labels_per_col
        col = (label_count // labels_per_col) % labels_per_row

        # Start a new page if we've filled the current one
        if label_count > 0 and label_count % (labels_per_row * labels_per_col) == 0:
            c.showPage()

        x = x_positions[col]
        y = y_positions[row]

        # Draw label border (optional, can be removed for cleaner look)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        c.setLineWidth(0.5)
        c.rect(x, y, label_width, label_height)

        # Draw child name (bold, larger font)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 14)
        child_name = f"{record.child.first_name} {record.child.last_name}"
        # Truncate if too long
        if len(child_name) > 25:
            child_name = child_name[:22] + "..."
        c.drawString(x + 0.1 * inch, y + label_height - 0.3 * inch, child_name)

        # Draw session name (smaller font)
        c.setFont("Helvetica", 10)
        session_name = record.session.name
        if len(session_name) > 30:
            session_name = session_name[:27] + "..."
        c.drawString(x + 0.1 * inch, y + label_height - 0.5 * inch, session_name)

        # Draw allergies/notes if present (smaller, red for allergies)
        text_y = y + label_height - 0.7 * inch
        if record.child.allergies:
            c.setFillColorRGB(0.8, 0, 0)  # Red for allergies
            c.setFont("Helvetica-Bold", 8)
            allergy_text = f"ALLERGY: {record.child.allergies}"
            if len(allergy_text) > 35:
                allergy_text = allergy_text[:32] + "..."
            c.drawString(x + 0.1 * inch, text_y, allergy_text)
            text_y -= 0.15 * inch

        # Generate QR code
        # Use production URL or localhost for dev - adjust as needed
        qr_code_str = (
            record.qr_code.code
            if hasattr(record, "qr_code") and record.qr_code
            else "INVALID"
        )
        qr_url = f"http://localhost:8080/qr/{qr_code_str}"

        qr = QrCodeWidget(qr_url)
        qr.barWidth = 1.1 * inch
        qr.barHeight = 1.1 * inch

        d = Drawing()
        d.add(qr)
        # Position QR code on the right side of the label
        renderPDF.draw(d, c, x + label_width - 1.25 * inch, y + 0.2 * inch)

        label_count += 1

    # Save the PDF
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
