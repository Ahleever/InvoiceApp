from flask import Flask, render_template, request, send_file, abort
from io import BytesIO
import json, os
from invoice_core import generate_invoice_pdf

app = Flask(__name__)

def parse_items_txt(file_stream):
    """
    Parse a dummy .txt file with format like:
      Customer Name: John Doe
      Customer Address: 123 Main St
      Items:
      Widget, 2, 15.00
      Service, 1, 50.00
    """
    items = []
    customer_name, customer_address = "", ""
    items_section = False

    for raw_line in file_stream.read().decode("utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Customer Name:"):
            customer_name = line.replace("Customer Name:", "").strip()
        elif line.startswith("Customer Address:"):
            customer_address = line.replace("Customer Address:", "").strip()
        elif line.startswith("Items:"):
            items_section = True
        elif items_section:
            parts = line.split(",")
            if len(parts) == 3:
                desc, qty, price = parts
                try:
                    qty = int(qty.strip())
                    price = float(price.strip())
                    items.append({"desc": desc.strip(), "qty": qty, "price": price})
                except Exception:
                    continue
    return customer_name, customer_address, items

@app.post("/generate")
def generate():
    dummy_file = request.files.get("dummy_file")

    if dummy_file:
        # If a dummy TXT file is uploaded, parse it
        customer_name, customer_address, items = parse_items_txt(dummy_file.stream)
        tax_rate = float(request.form.get("tax_rate") or "0")
    else:
        # Otherwise use form fields
        customer_name = (request.form.get("customer_name") or "").strip()
        customer_address = (request.form.get("customer_address") or "").strip()
        tax_rate = float(request.form.get("tax_rate") or "0")
        items_csv = request.form.get("items_csv") or ""
        items = []
        for line in items_csv.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                desc, qty, price = parts
                try:
                    items.append({"desc": desc, "qty": int(qty), "price": float(price)})
                except:
                    pass

    if not customer_name or not customer_address or not items:
        return abort(400, "Missing customer info or items.")

    wm_path = os.path.join(app.static_folder, "watermark.png")
    if not os.path.exists(wm_path):
        wm_path = None

    pdf_bytes = generate_invoice_pdf(
        customer_name=customer_name,
        customer_address=customer_address,
        items=items,
        tax_rate=tax_rate,
        watermark_path=wm_path
    )

    fname_safe = f"{customer_name.replace(' ', '_')}_Invoice.pdf"
    return send_file(BytesIO(pdf_bytes),
                     mimetype="application/pdf",
                     as_attachment=True,
                     download_name=fname_safe)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
