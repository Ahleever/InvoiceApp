from flask import Flask, render_template, request, send_file, abort
from io import BytesIO
import os, json, sys
from invoice_core import generate_invoice_pdf

app = Flask(__name__)

def parse_dummy_file(file_storage):
    """
    Parse TXT like:
      Customer Name: John Doe
      Customer Address: 123 Main St
      Items:
      Item A, 2, 10.5
      Item B, 1, 99
    """
    if not file_storage:
        return None, None, []
    data = file_storage.read()
    # robust decode
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1", errors="ignore")

    items = []
    name = address = ""
    items_section = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("Customer Name:"):
            name = line.replace("Customer Name:", "").strip()
        elif line.startswith("Customer Address:"):
            address = line.replace("Customer Address:", "").strip()
        elif line.startswith("Items:"):
            items_section = True
        elif items_section:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                desc, qty, price = parts
                try:
                    items.append({"desc": desc, "qty": int(qty), "price": float(price)})
                except Exception:
                    continue
    return name, address, items

@app.get("/")
def index():
    return render_template("form.html")

@app.post("/generate")
def generate():
    try:
        # Prefer dummy file if provided
        dummy_file = request.files.get("dummy_file")
        if dummy_file and dummy_file.filename:
            customer_name, customer_address, items = parse_dummy_file(dummy_file)
            tax_rate = float(request.form.get("tax_rate") or "0")
        else:
            # Fall back to form inputs
            customer_name = (request.form.get("customer_name") or "").strip()
            customer_address = (request.form.get("customer_address") or "").strip()
            tax_rate = float(request.form.get("tax_rate") or "0")

            mode = request.form.get("items_mode", "csv")
            if mode == "json":
                try:
                    items = json.loads(request.form.get("items_json") or "[]")
                except json.JSONDecodeError:
                    return abort(400, "Invalid JSON for items.")
            else:
                items = []
                for line in (request.form.get("items_csv") or "").splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) == 3:
                        desc, qty, price = parts
                        try:
                            items.append({"desc": desc, "qty": int(qty), "price": float(price)})
                        except Exception:
                            pass

        if not customer_name or not customer_address or not items:
            return abort(400, "Missing customer info or items.")

        wm_path = os.path.join(app.static_folder or "static", "watermark.png")
        if not os.path.exists(wm_path):
            wm_path = None

        pdf_bytes = generate_invoice_pdf(
            customer_name=customer_name,
            customer_address=customer_address,
            items=items,
            tax_rate=tax_rate,
            watermark_path=wm_path
        )

        fname = f"{customer_name.replace(' ', '_')}_Invoice.pdf" or "Invoice.pdf"
        return send_file(BytesIO(pdf_bytes),
                         mimetype="application/pdf",
                         as_attachment=True,
                         download_name=fname)

    except Exception as e:
        # log full stack to Render logs
        print("ERROR /generate:", e, file=sys.stderr)
        import traceback; traceback.print_exc()
        return abort(500, "Server error while generating invoice.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
