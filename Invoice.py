import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import StringVar
from tkinter.ttk import Combobox
import re
import os
import json
from decimal import Decimal, InvalidOperation
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas # type: ignore
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import traceback

class InvoiceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Custom Kitchen Cabinets")
        self.geometry("900x700")
        self.items = []
        self.selected_item_index = None

        self.default_invoice_dir = r"C:\\Invoices"
        os.makedirs(self.default_invoice_dir, exist_ok=True)

        tk.Label(self, text="Customer Name:").grid(row=0, column=0, sticky="e")
        self.customer_name = tk.Entry(self, width=40)
        self.customer_name.grid(row=0, column=1, columnspan=2, pady=5, sticky="w")

        tk.Label(self, text="Customer Address:").grid(row=1, column=0, sticky="e")
        self.customer_address = tk.Entry(self, width=40)
        self.customer_address.grid(row=1, column=1, columnspan=2, pady=5, sticky="w")

        tk.Button(self, text="Load Invoice", command=self.load_invoice_data).grid(row=0, column=3, padx=10)
        tk.Button(self, text="Load Dummy Data", command=self.load_dummy_data).grid(row=1, column=3, padx=10)

        tk.Label(self, text="Item Description:").grid(row=2, column=0, pady=10, sticky="e")
        self.item_desc = tk.Entry(self, width=20)
        self.item_desc.grid(row=2, column=1, sticky="w")
        tk.Label(self, text="Quantity:").grid(row=2, column=2, sticky="e")
        self.item_qty = tk.Entry(self, width=5)
        self.item_qty.grid(row=2, column=3, sticky="w")
        tk.Label(self, text="Unit Price:").grid(row=2, column=4, sticky="e")
        self.item_price = tk.Entry(self, width=7)
        self.item_price.grid(row=2, column=5, sticky="w")

        tk.Button(self, text="Add Item", command=self.add_item).grid(row=2, column=6, padx=5)
        tk.Button(self, text="Delete Item", command=self.delete_selected_item).grid(row=2, column=7, padx=5)

        self.tree = ttk.Treeview(self, columns=('Description', 'Quantity', 'Unit Price', 'Total'), show='headings')
        self.tree.heading('Description', text='Description')
        self.tree.heading('Quantity', text='Quantity')
        self.tree.heading('Unit Price', text='Unit Price')
        self.tree.heading('Total', text='Total')
        self.tree.grid(row=3, column=0, columnspan=9, pady=10, sticky="ew")
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        tk.Label(self, text="Tax Rate (%):").grid(row=4, column=0, sticky="e")
        self.tax_rate_var = StringVar(value="0.0")
        self.tax_rate_entry = tk.Entry(self, textvariable=self.tax_rate_var, width=10)
        self.tax_rate_entry.grid(row=4, column=1, sticky="w")
        self.tax_rate_var.trace_add("write", lambda *args: self.generate_invoice())

        #tk.Button(self, text="Generate Invoice", command=self.generate_invoice).grid(row=4, column=0, pady=15, columnspan=9)

        self.invoice_text = tk.Text(self, height=12, width=70, bd=2, relief="ridge", highlightthickness=2, highlightbackground="#0077cc")
        self.invoice_text.grid(row=5, column=0, columnspan=9, padx=10, pady=10)

        tk.Button(self, text="Export as PDF", command=self.export_as_pdf).grid(row=6, column=1, pady=10, sticky="e")
        tk.Button(self, text="Save For Later", command=self.save_invoice_data).grid(row=6, column=4, pady=10, sticky="w")

        #for history
        self.desc_var = StringVar()
        self.item_desc = Combobox(self, textvariable=self.desc_var, width=20)
        self.item_desc.grid(row=2, column=1, sticky="w")
        self.item_desc['values'] = []  # This will hold history
        self.desc_history = set()
        self.history_file = os.path.join(self.default_invoice_dir, "desc_history.json")
        self.load_description_history()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_description_history(self):
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, "r") as f:
                    history = json.load(f)
                    self.desc_history = set(history)
                    self.item_desc['values'] = sorted(self.desc_history)
        except Exception as e:
            traceback.print_exc()
            messagebox.showwarning("History Load Error", f"Could not load description history.\n{e}")

    def save_description_history(self):
        try:
            with open(self.history_file, "w") as f:
                json.dump(sorted(self.desc_history), f, indent=2)
        except Exception as e:
            traceback.print_exc()
            messagebox.showwarning("History Save Error", f"Could not save description history.\n{e}")

    def on_close(self):
        self.save_description_history()
        self.destroy()

    @staticmethod
    def sanitize_filename(s):
        return re.sub(r'[^a-zA-Z0-9_]', '', s.replace(" ", "_"))

    def get_invoice_filename(self, ext="pdf"):
        name = self.sanitize_filename(self.customer_name.get())
        address = self.sanitize_filename(self.customer_address.get())
        return f"{name}_{address}_Invoice.{ext}"

    def get_inprogress_filename(self, ext="json"):
        name = self.sanitize_filename(self.customer_name.get())
        address = self.sanitize_filename(self.customer_address.get())
        return f"InProgress_{name}_{address}_Invoice.{ext}"
    
    def load_dummy_data(self):
        file_path = filedialog.askopenfilename(
            title="Select Dummy Data File", filetypes=[("Text Files", "*.txt")]
        )
        if not file_path:
            return
        try:
            with open(file_path, "r") as f:
                lines = f.readlines()
            self.items.clear()
            self.tree.delete(*self.tree.get_children())

            items_section = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("Customer Name:"):
                    self.customer_name.delete(0, tk.END)
                    self.customer_name.insert(0, line.replace("Customer Name:", "").strip())
                elif line.startswith("Customer Address:"):
                    self.customer_address.delete(0, tk.END)
                    self.customer_address.insert(0, line.replace("Customer Address:", "").strip())
                elif line.startswith("Items:"):
                    items_section = True
                elif items_section:
                    parts = line.split(",")
                    if len(parts) == 3:
                        desc, qty, price = parts
                        try:
                            qty = int(qty.strip())
                            price = float(price.strip())
                            total = qty * price
                            item = {'desc': desc.strip(), 'qty': qty, 'price': price, 'total': total}
                            self.items.append(item)
                            self.tree.insert('', 'end', values=(item['desc'], item['qty'], f"{item['price']:.2f}", f"{item['total']:.2f}"))
                        except Exception:
                            continue
            self.generate_invoice()
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Load Dummy Data Error", str(e))

    def add_item(self):
        desc = self.item_desc.get().strip()
        if not desc:
            messagebox.showerror("Input Error", "Item description cannot be empty.")
            return
        try:
            qty = int(self.item_qty.get())
            price = Decimal(self.item_price.get())
            if qty < 1 or price < 0:
                raise ValueError
        except (ValueError, InvalidOperation):
            messagebox.showerror("Input Error", "Please enter valid quantity and price.")
            return

        total = qty * price
        item = {'desc': desc, 'qty': qty, 'price': float(price), 'total': float(total)}
        self.items.append(item)
        self.tree.insert('', 'end', values=(desc, qty, f"{price:.2f}", f"{total:.2f}"))
        self.item_desc.delete(0, tk.END)
        self.item_qty.delete(0, tk.END)
        self.item_price.delete(0, tk.END)

        if desc not in self.desc_history:
            self.desc_history.add(desc)
            self.item_desc['values'] = sorted(self.desc_history)
            self.save_description_history()
        
        self.generate_invoice()

    def delete_selected_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selection Error", "No item selected.")
            return
        for item_id in selected:
            index = self.tree.index(item_id)
            self.tree.delete(item_id)
            if index < len(self.items):
                del self.items[index]
        self.generate_invoice()

    def on_tree_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        col_index = int(col.replace("#", "")) - 1
        if col_index not in [1, 2]:
            return

        x, y, width, height = self.tree.bbox(row_id, col)
        item_index = self.tree.index(row_id)
        value = self.tree.item(row_id, "values")[col_index]

        entry = tk.Entry(self.tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, value)
        entry.focus_set()

        def save_edit(event=None):
            new_value = entry.get()
            try:
                if col_index == 1:
                    new_qty = int(new_value)
                    self.items[item_index]['qty'] = new_qty
                elif col_index == 2:
                    new_price = Decimal(new_value)
                    self.items[item_index]['price'] = float(new_price)
            except (ValueError, InvalidOperation):
                messagebox.showerror("Input Error", "Please enter a valid number.")
                entry.destroy()
                return
            self.items[item_index]['total'] = self.items[item_index]['qty'] * self.items[item_index]['price']
            self.tree.item(row_id, values=(
                self.items[item_index]['desc'],
                self.items[item_index]['qty'],
                f"{self.items[item_index]['price']:.2f}",
                f"{self.items[item_index]['total']:.2f}"
            ))
            entry.destroy()
            self.generate_invoice()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", lambda e: entry.destroy())

    def generate_invoice(self):
            name = self.customer_name.get()
            address = self.customer_address.get()
            if not name or not address or not self.items:
                return

            try:
                tax_rate = float(self.tax_rate_var.get()) / 100.0
            except ValueError:
                tax_rate = 0.0

            invoice = f"INVOICE\nCustomer: {name}\nAddress: {address}\n\n"
            invoice += "Items:\n"
            invoice += "{:<20} {:<10} {:<12} {:<10}\n".format('Description', 'Quantity', 'Unit Price', 'Total')
            invoice += "-"*60 + "\n"
            subtotal = 0
            for item in self.items:
                invoice += "{:<20} {:<10} {:<12.2f} {:<10.2f}\n".format(item['desc'], item['qty'], item['price'], item['total'])
                subtotal += item['total']

            tax_amount = subtotal * tax_rate
            grand_total = subtotal + tax_amount

            invoice += "-"*60 + "\n"
            invoice += f"Subtotal: ${subtotal:.2f}\n"
            invoice += f"Tax ({self.tax_rate_var.get()}%): ${tax_amount:.2f}\n"
            invoice += f"Grand Total: ${grand_total:.2f}\n"

            self.invoice_text.delete('1.0', tk.END)
            self.invoice_text.insert(tk.END, invoice)

    def save_invoice_data(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile=self.get_inprogress_filename(),
                initialdir=self.default_invoice_dir
            )
            if not file_path:
                return
            with open(file_path, "w") as f:
                json.dump({
                    "customer_name": self.customer_name.get(),
                    "customer_address": self.customer_address.get(),
                    "items": self.items
                }, f, indent=2)
            messagebox.showinfo("Invoice Saved", f"Invoice data saved to {file_path}")
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Save Error", str(e))

    def load_invoice_data(self):
        try:
            file_path = filedialog.askopenfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialdir=self.default_invoice_dir
            )
            if not file_path:
                return
            with open(file_path, "r") as f:
                data = json.load(f)
            self.customer_name.delete(0, tk.END)
            self.customer_name.insert(0, data.get("customer_name", ""))
            self.customer_address.delete(0, tk.END)
            self.customer_address.insert(0, data.get("customer_address", ""))
            self.items = data.get("items", [])
            self.tree.delete(*self.tree.get_children())
            for item in self.items:
                self.tree.insert('', 'end', values=(item['desc'], item['qty'], f"{item['price']:.2f}", f"{item['total']:.2f}"))
            self.generate_invoice()
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Load Error", str(e))

    def export_as_pdf(self, file_path=None, show_message=True):
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors

        default_name = self.get_invoice_filename()
        initialdir = self.default_invoice_dir if os.path.exists(self.default_invoice_dir) else os.getcwd()
        if not file_path:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")], initialfile=default_name, initialdir=initialdir
            )
        if not file_path:
            return None
        try:
            c = canvas.Canvas(file_path, pagesize=landscape(letter))
            width, height = landscape(letter)

            watermark_path = "watermark.png"
            def draw_watermark():
                if os.path.exists(watermark_path):
                    img = ImageReader(watermark_path)
                    img_width, img_height = img.getSize()
                    scale = min(width / img_width, height / img_height) * 0.7
                    wm_width = img_width * scale
                    wm_height = img_height * scale
                    wm_x = (width - wm_width) / 2
                    wm_y = (height - wm_height) / 2
                    c.saveState()
                    c.translate(wm_x, wm_y)
                    c.setFillAlpha(0.15)
                    c.drawImage(img, 0, 0, width=wm_width, height=wm_height, mask='auto')
                    c.restoreState()

            # Prepare table data
            data = [['Description', 'Quantity', 'Unit Price', 'Total']]
            for item in self.items:
                data.append([
                    str(item['desc']),
                    str(item['qty']),
                    f"${item['price']:.2f}",
                    f"${item['total']:.2f}"
                ])
            data.append(['', '', 'Grand Total:', f"${sum(item['total'] for item in self.items):,.2f}"])

            table_col_widths = [380, 100, 100, 100]
            row_height = 24

            # First page: headers and business info
            y_start_first = height - 120
            bottom_margin = 20
            max_rows_first = int((y_start_first - bottom_margin) / row_height)

            # Later pages: only table, start higher
            y_start_other = height - 10
            max_rows_other = int((y_start_other - bottom_margin) / row_height)

            data_body = data[1:-1]
            header = data[0]
            grand_total = data[-1]

            i = 0
            first_page = True
            while i < len(data_body):
                c.setFont("Helvetica", 12)

                if first_page:
                    draw_watermark()
                    c.setFont("Times-Italic", 40)
                    company_name = "Custom Kitchen Cabinets"
                    company_name_width = c.stringWidth(company_name, "Times-Italic", 40)
                    c.drawString((width - company_name_width) / 2, height - 175, company_name)

                    c.setFont("Helvetica-Bold", 20)
                    invoice_text = "INVOICE"
                    invoice_width = c.stringWidth(invoice_text, "Helvetica-Bold", 30)
                    c.drawString((width - invoice_width) / 2, height - 60, invoice_text)

                    c.setFont("Helvetica", 14)
                    c.drawString(60, height - 110, f"Customer: {self.customer_name.get()}")
                    c.drawString(60, height - 130, f"Address: {self.customer_address.get()}")

                    y_start = y_start_first
                    max_rows = max_rows_first
                else:
                    draw_watermark()
                    y_start = y_start_other
                    max_rows = max_rows_other

                table_rows = data_body[i:i + (max_rows - 2)]
                page_data = [header] + table_rows
                is_last_page = (i + (max_rows - 2)) >= len(data_body)
                if is_last_page:
                    page_data.append(grand_total)
                table = Table(page_data, colWidths=table_col_widths, hAlign='CENTER')
                grand_total_row = len(page_data) - 1 if is_last_page else None
                style = [
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('ALIGN', (1,1), (-1,-2 if is_last_page else -1), 'RIGHT'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ]
                if grand_total_row is not None:
                    style.append(('FONTNAME', (0,grand_total_row), (-1,grand_total_row), 'Helvetica-Bold'))
                    style.append(('BACKGROUND', (0,grand_total_row), (-1,grand_total_row), colors.whitesmoke))
                table.setStyle(TableStyle(style))
                table_height = row_height * len(page_data)
                table.wrapOn(c, width, height)
                total_table_width = sum(table_col_widths)
                x_center = (width - total_table_width) / 2
                table.drawOn(c, x_center, y_start - table_height)

                i += (max_rows - 2)
                first_page = False
                if not is_last_page:
                    c.showPage()
                    

            c.save()
            return file_path
        except Exception as e:
            messagebox.showerror("PDF Export Error: Close PDF", str(e))
            return None

if __name__ == "__main__":
    app = InvoiceApp()
    app.mainloop()