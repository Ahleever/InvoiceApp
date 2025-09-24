# invoice_core.py
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

def generate_invoice_pdf(customer_name, customer_address, items, tax_rate=0.0, watermark_path=None):
    """
    items: list of dicts with keys: desc(str), qty(int), price(float)
    tax_rate: e.g. 8.25 for 8.25%
    return: bytes of the PDF file
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=landscape(letter))
    width, height = landscape(letter)

    def draw_watermark():
        if watermark_path:
            try:
                img = ImageReader(watermark_path)
                img_width, img_height = img.getSize()
                scale = min(width / img_width, height / img_height) * 0.7
                wm_width = img_width * scale
                wm_height = img_height * scale
                wm_x = (width - wm_width) / 2
                wm_y = (height - wm_height) / 2
                c.saveState()
                # alpha may not always be supported in some renderers; if not, just draw image.
                try:
                    c.setFillAlpha(0.15)
                except Exception:
                    pass
                c.drawImage(img, wm_x, wm_y, width=wm_width, height=wm_height, mask='auto')
                c.restoreState()
            except Exception:
                pass

    # Table data
    data = [['Description', 'Quantity', 'Unit Price', 'Total']]
    subtotal = 0.0
    for it in items:
        line_total = float(it['qty']) * float(it['price'])
        subtotal += line_total
        data.append([
            str(it['desc']),
            str(it['qty']),
            f"${float(it['price']):.2f}",
            f"${line_total:.2f}",
        ])

    tax_amount = subtotal * (float(tax_rate) / 100.0)
    grand_total_val = subtotal + tax_amount
    data.append(['', '', 'Subtotal:', f"${subtotal:,.2f}"])
    data.append(['', '', f"Tax ({tax_rate:.2f}%):", f"${tax_amount:,.2f}"])
    data.append(['', '', 'Grand Total:', f"${grand_total_val:,.2f}"])

    table_col_widths = [380, 100, 100, 120]
    row_height = 24

    # First page has header
    y_start_first = height - 120
    bottom_margin = 20
    max_rows_first = int((y_start_first - bottom_margin) / row_height)

    # Later pages: table starts higher
    y_start_other = height - 10
    max_rows_other = int((y_start_other - bottom_margin) / row_height)

    # Split data: header + body rows
    header = data[0]
    body = data[1:-3]
    totals = data[-3:]  # subtotal, tax, grand total

    i = 0
    first_page = True
    while True:
        c.setFont("Helvetica", 12)
        draw_watermark()

        if first_page:
            # Company title
            c.setFont("Times-Italic", 40)
            company_name = "Custom Kitchen Cabinets"
            company_name_width = c.stringWidth(company_name, "Times-Italic", 40)
            c.drawString((width - company_name_width) / 2, height - 175, company_name)

            # INVOICE label
            c.setFont("Helvetica-Bold", 20)
            invoice_text = "INVOICE"
            invoice_width = c.stringWidth(invoice_text, "Helvetica-Bold", 20)
            c.drawString((width - invoice_width) / 2, height - 60, invoice_text)

            # Customer lines
            c.setFont("Helvetica", 14)
            c.drawString(60, height - 110, f"Customer: {customer_name}")
            c.drawString(60, height - 130, f"Address:  {customer_address}")

            y_start = y_start_first
            max_rows = max_rows_first
        else:
            y_start = y_start_other
            max_rows = max_rows_other

        # Leave 1 row for header + (max_rows - 1) for data; reserve 3 rows for totals on last page
        rows_available_for_data = max_rows - 1
        # If this is the last chunk, include totals too
        remaining = len(body) - i
        fits_with_totals = remaining <= (rows_available_for_data - 3)
        take = min(remaining, rows_available_for_data - (3 if fits_with_totals else 0))

        page_rows = body[i:i+take]
        page_data = [header] + page_rows
        if i + take >= len(body):
            # last page -> add totals
            page_data += totals

        table = Table(page_data, colWidths=table_col_widths, hAlign='CENTER')
        style = [
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]
        if i + take >= len(body):
            # bold totals
            last_rows = len(page_data) - 3, len(page_data) - 2, len(page_data) - 1
            for r in last_rows:
                style.append(('FONTNAME', (0,r), (-1,r), 'Helvetica-Bold'))
                style.append(('BACKGROUND', (0,r), (-1,r), colors.whitesmoke))
        table.setStyle(TableStyle(style))

        table_height = row_height * len(page_data)
        total_table_width = sum(table_col_widths)
        x_center = (width - total_table_width) / 2
        table.wrapOn(c, width, height)
        table.drawOn(c, x_center, y_start - table_height)

        i += take
        if i >= len(body):
            break
        first_page = False
        c.showPage()

    c.save()
    buf.seek(0)
    return buf.getvalue()
