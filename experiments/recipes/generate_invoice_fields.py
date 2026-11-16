"""Generate the synthetic invoice-fields example dataset without external data."""
from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "invoice-fields"
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Distinct presentation patterns for the held-out split are kept separate.
TRAIN = [
    "TAX INVOICE\nVendor: {vendor}\nInvoice No: {invoice_no}\nDate: {date}\nGSTIN: {gstin}\nGrand Total: ₹{total}",
    "{vendor}\nGSTIN {gstin}\nInvoice #{invoice_no}\nIssued {date}\nTotal due INR {total}",
    "Bill from {vendor}; bill number {invoice_no}; date {date}; tax ID {gstin}; amount payable ₹{total}.",
    "Supplier: {vendor} | GSTIN: {gstin} | Invoice: {invoice_no} | Invoice date: {date} | Total: {total}",
    "Invoice {invoice_no} dated {date}\nSeller {vendor}\nGST number {gstin}\nAmount due: INR {total}",
    "{vendor} | Tax invoice\n{invoice_no} - {date}\nGSTIN {gstin}\nNet amount payable Rs {total}",
    "Receipt of invoice: seller={vendor}; ref={invoice_no}; issued={date}; gstin={gstin}; total=₹{total}",
    "From: {vendor}\nDocument: {invoice_no}\nDated: {date}\nRegistered GSTIN: {gstin}\nPayable: {total} INR",
    "Vendor name {vendor}. Invoice number {invoice_no}. Date of issue {date}. GSTIN {gstin}. Total INR {total}.",
    "{vendor}\nTax ID: {gstin}\nBill ref: {invoice_no}\nBilling date: {date}\nAmount including tax: ₹{total}",
    "INVOICE\n{invoice_no}\n{date}\nBilled by {vendor}\nGSTIN {gstin}\nTotal payment Rs {total}",
    "Invoice details: {invoice_no}, {date}, {vendor}, GSTIN {gstin}; total billed INR {total}.",
    "Seller\n{vendor}\nReference\n{invoice_no}\nIssued on\n{date}\nGSTIN\n{gstin}\nTotal\n{total}",
    "{vendor} raised invoice {invoice_no} on {date}. GSTIN {gstin}. Total charged: ₹{total}.",
    "Bill no. {invoice_no} / date {date}\nIssued by {vendor}\nGSTIN: {gstin}\nFinal total: Rs {total}",
    "Invoice ID={invoice_no} | Seller={vendor} | Issued={date} | GSTIN={gstin} | Total INR={total}",
    "Payment statement for {vendor}: document {invoice_no} dated {date}; GSTIN {gstin}; payable {total} INR.",
    "Tax bill from {vendor}\nNo. {invoice_no}\nDate {date}\nRegistration {gstin}\nTotal due ₹{total}",
    "{date}\nInvoice {invoice_no}\n{vendor}\nGST registration {gstin}\nBalance to pay: Rs {total}",
    "Document type: invoice; supplier: {vendor}; document no: {invoice_no}; date: {date}; GSTIN: {gstin}; gross: {total} INR",
]
TEST = [
    "Please process the invoice received from {vendor}. Its reference is {invoice_no}, issued on {date}; the GSTIN is {gstin} and the amount due is ₹{total}.",
    "Accounts payable entry\nRegistered supplier: {vendor}\nTax registration: {gstin}\nDocument date: {date}\nReference: {invoice_no}\nPay this amount: INR {total}",
    "Amount payable Rs {total} against {invoice_no}. Issued on {date} by {vendor}, GSTIN {gstin}.",
    "Seller information [{vendor}; {gstin}]\nInvoice identification [{invoice_no}; {date}]\nTotal including GST [{total} INR]",
    "For the books: {vendor} submitted invoice {invoice_no} dated {date}. Record GSTIN {gstin} and a final amount of Rs {total}.",
]


def gstin_check_character(first_fourteen: str) -> str:
    factor = 1
    total = 0
    for char in first_fourteen:
        product = ALPHABET.index(char) * factor
        total += product // 36 + product % 36
        factor = 1 if factor == 2 else 2
    return ALPHABET[(36 - total % 36) % 36]


def example(index: int) -> dict[str, str]:
    # Invented tax IDs have the standard 15-character shape but deliberately fail
    # the check digit. This prevents a generated value from being a real GSTIN.
    prefix = f"27ZZZPZ{index:04d}Z1Z"
    correct = gstin_check_character(prefix)
    dummy = ALPHABET[(ALPHABET.index(correct) + 1) % 36]
    return {
        "vendor": f"Zevix Sample Supplier {index:03d}",
        "invoice_no": f"TEST-{index:05d}",
        "date": (date(2024, 1, 1) + timedelta(days=index)).isoformat(),
        "total": f"{100 + index * 7}.{(index * 13) % 100:02d}",
        "gstin": prefix + dummy,
    }


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for split, layouts, start in (("train", TRAIN, 1), ("test", TEST, 201)):
        with (ROOT / f"{split}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["text", "json"])
            writer.writeheader()
            for layout_index, layout in enumerate(layouts):
                for variant in range(10):
                    values = example(start + layout_index * 10 + variant)
                    writer.writerow({"text": layout.format(**values), "json": json.dumps(values, ensure_ascii=False)})
        print(f"{split}: {len(layouts) * 10} examples")


if __name__ == "__main__":
    main()
