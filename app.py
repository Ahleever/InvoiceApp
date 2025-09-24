# app.py
from flask import Flask, render_template, request, send_file, abort
from io import BytesIO
import json, os
from invoice_core import generate_invoice_pdf

app = Flask(__name__)

@app.get("/")
def index():
    return render_template("form.html")

def parse_items_csv(csv_text):
    """
    CSV-like lines: Description, Quantity, UnitPrice
    Example:
      Upper Cabinets, 5, 1200
      Install, 1, 800
    """
    items = []
    for line in csv_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            continue
        desc, qty, price = parts
        try:
            items.append({"desc": desc, "qty": int(qty), "price": float(price)})
        except Exception:
            continue
    return items

@app.post("/generate")
def generate():
    customer_name = (request.form.get("customer_name") or "").strip()
    customer_address = (request.form.get("customer_address") or "").strip()
    tax_rate = float(request.form.get("tax_rate") or "0")
    items_mode = request.form.get("items_mode", "csv")

    if items_mode == "json":
        try:
            items = json.loads(request.form.get("items_json") or "[]")
        except json.JSONDecodeError:
            return abort(400, "Invalid JSON for items.")
    else:
        items_csv = request.form.get("items_csv") or ""
        items = parse_items_csv(items_csv)

    if not customer_name or not customer_address or not items:
        return abort(400, "Missing customer info or items.")

    # watermark in /static
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
