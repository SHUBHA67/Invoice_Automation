import sqlite3
from fpdf import FPDF
from datetime import datetime
from num2words import num2words
import streamlit as st
import os
import json
import pandas as pd
# ---------- Database Setup ----------
DB_FILE = "invoice_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        date TEXT,
        company_name TEXT,
        company_address TEXT,
        company_gstin TEXT,
        buyer_name TEXT,
        buyer_address TEXT,
        items TEXT,
        subtotal REAL,
        cgst REAL,
        sgst REAL,
        total REAL
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- PDF Class ----------
class InvoicePDF(FPDF):
    def header(self):
        self.set_font("Times", "B", 20)
        self.cell(0, 10, "Tax Invoice", ln=True)
        self.ln(3)
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, self.company_name, ln=True)
        self.set_font("Arial", "", 10)
        self.cell(0, 6, self.company_address, ln=True)
        self.cell(0, 6, f"GSTIN: {self.company_gstin}", ln=True)
        self.ln(5)

    def add_buyer_details(self, name, address):
        self.set_font("Arial", "B", 12)
        self.cell(0, 6, "Bill To:", ln=True)
        self.set_font("Arial", "", 10)
        self.cell(0, 6, f"{name}", ln=True)
        self.cell(0, 6, f"{address}", ln=True)
        self.ln(5)

    def add_invoice_info(self, invoice_no, date_str):
        self.set_font("Arial", "", 10)
        self.cell(0, 6, f"Invoice No: {invoice_no}", ln=True)
        self.cell(0, 6, f"Date: {date_str}", ln=True)
        self.ln(5)

    def add_table_header(self):
        self.set_fill_color(200, 220, 255)
        self.set_font("Arial", "B", 10)
        self.cell(10, 8, "No", 1, 0, "C", 1)
        self.cell(60, 8, "Item", 1, 0, "C", 1)
        self.cell(20, 8, "Qty", 1, 0, "C", 1)
        self.cell(30, 8, "Rate", 1, 0, "C", 1)
        self.cell(30, 8, "Total", 1, 1, "C", 1)

    def add_table_row(self, no, item, qty, rate):
        total = qty * rate
        self.set_font("Arial", "", 10)
        self.cell(10, 8, str(no), 1)
        self.cell(60, 8, item, 1)
        self.cell(20, 8, str(qty), 1, 0, "R")
        self.cell(30, 8, f"{rate:.2f}", 1, 0, "R")
        self.cell(30, 8, f"{total:.2f}", 1, 1, "R")
        return total

    def add_totals(self, subtotal):
        cgst = subtotal * 0.09
        sgst = subtotal * 0.09
        grand_total = subtotal + cgst + sgst

        self.ln(2)
        self.cell(80)
        self.cell(40, 8, "Subtotal", 1)
        self.cell(30, 8, f"{subtotal:.2f}", 1, 1, "R")

        self.cell(80)
        self.cell(40, 8, "CGST (9%)", 1)
        self.cell(30, 8, f"{cgst:.2f}", 1, 1, "R")

        self.cell(80)
        self.cell(40, 8, "SGST (9%)", 1)
        self.cell(30, 8, f"{sgst:.2f}", 1, 1, "R")

        self.cell(80)
        self.set_font("Arial", "B", 10)
        self.cell(40, 8, "Total", 1)
        self.cell(30, 8, f"{grand_total:.2f}", 1, 1, "R")

        self.ln(5)
        self.set_font("Arial", "I", 9)
        amount_words = num2words(grand_total, lang='en_IN').title() + " Rupees Only"
        self.cell(0, 6, f"Amount in words: {amount_words}", ln=True)


    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, "Thank you for your business!", 0, 0, "C")

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Invoice Generator", layout="centered")
st.title("🧾 Invoice Generator")

menu = st.sidebar.selectbox("Select Action", ["Create Invoice", "View Invoice Database"])

if menu == "Create Invoice":
    st.header("Company Details")
    company_name = st.text_input("Company Name")
    company_address = st.text_area("Company Address")
    company_gstin = st.text_input("Company GSTIN")

    st.header("Buyer Details")
    buyer_name = st.text_input("Buyer Name")
    buyer_address = st.text_area("Buyer Address")

    st.header("Invoice Info")
    invoice_no = st.text_input("Invoice Number")
    date_str = st.date_input("Invoice Date").strftime("%d-%m-%Y")

    st.header("Items")
    items = []
    num_items = st.number_input("Number of items", min_value=1, step=1)

    for i in range(int(num_items)):
        st.subheader(f"Item {i+1}")
        item_name = st.text_input(f"Item Name {i+1}", key=f"item_name_{i}")
        qty = st.number_input(f"Quantity {i+1}", min_value=1, step=1, key=f"qty_{i}")
        rate = st.number_input(f"Rate {i+1}", min_value=0.0, step=0.01, key=f"rate_{i}")
        items.append({"name": item_name, "qty": qty, "rate": rate})

    if st.button("Generate Invoice"):
        subtotal = sum(item["qty"] * item["rate"] for item in items)
        cgst = subtotal * 0.09
        sgst = subtotal * 0.09
        grand_total = subtotal + cgst + sgst

        # Save to DB
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO invoices (
                invoice_no, date, company_name, company_address, company_gstin,
                buyer_name, buyer_address, items, subtotal, cgst, sgst, total
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_no, date_str, company_name, company_address, company_gstin,
            buyer_name, buyer_address, json.dumps(items), subtotal, cgst, sgst, grand_total
        ))
        conn.commit()
        conn.close()

        # Generate PDF
        pdf = InvoicePDF()
        pdf.company_name = company_name
        pdf.company_address = company_address
        pdf.company_gstin = company_gstin

        pdf.add_page()
        pdf.add_invoice_info(invoice_no, date_str)
        pdf.add_buyer_details(buyer_name, buyer_address)
        pdf.add_table_header()

        for idx, item in enumerate(items, 1):
            pdf.add_table_row(idx, item["name"], item["qty"], item["rate"])

        pdf.add_totals(subtotal)

        filename = f"{invoice_no}.pdf"
        pdf.output(filename)

        st.success("✅ Invoice generated and saved to database.")
        with open(filename, "rb") as f:
            st.download_button("📥 Download Invoice PDF", f, file_name=filename, mime="application/pdf")

elif menu == "View Invoice Database":
    conn = sqlite3.connect(DB_FILE)
    data = conn.execute("SELECT invoice_no, date, company_name, buyer_name, total FROM invoices").fetchall()
    conn.close()

    if data:
        st.subheader("📋 Stored Invoices")

        df = pd.DataFrame(data, columns=["Invoice No", "Date", "Company", "Buyer", "Total"])
        st.dataframe(df)

        selected_invoice = st.selectbox("Select Invoice to Download", df["Invoice No"])

        pdf_path = f"{selected_invoice}.pdf"
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label=f"📥 Download Invoice {selected_invoice}",
                    data=f,
                    file_name=pdf_path,
                    mime="application/pdf"
                )
        else:
            st.error("PDF file not found for selected invoice.")
    else:
        st.info("No invoices found.")
