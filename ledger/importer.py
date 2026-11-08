"""Parse a bank-statement CSV into transaction rows.

Expected columns (case-insensitive header): date, amount, description, and optionally category.
Dates: YYYY-MM-DD or DD/MM/YYYY. Amounts: negative = expense, positive = income;
"1 200,50" and "1,200.50" are both understood.
"""

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import Transaction

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")
REQUIRED_COLUMNS = {"date", "amount", "description"}
MAX_ROWS = 5000
CENT = Decimal("0.01")


def parse_date(value):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date '{value}' (use YYYY-MM-DD or DD/MM/YYYY)")


def parse_amount(value):
    cleaned = value.replace(" ", "").replace(" ", "")
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"invalid amount '{value}'")
    if not amount.is_finite() or abs(amount) >= Decimal("1e10"):
        raise ValueError(f"invalid amount '{value}'")
    amount = amount.quantize(CENT)
    if amount == 0:
        raise ValueError("amount is zero")
    return amount


def parse_csv(text, categories):
    """Return (rows, errors). `categories` maps lower-case name -> Category.

    Nothing should be saved unless `errors` is empty.
    """
    reader = csv.DictReader(io.StringIO(text))
    headers = {(h or "").strip().lower() for h in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        return [], [f"Missing column(s): {', '.join(sorted(missing))}"]

    rows, errors = [], []
    for line_no, raw in enumerate(reader, start=2):
        if line_no > MAX_ROWS + 1:
            errors.append(f"Too many rows (maximum {MAX_ROWS}).")
            break
        row = {}
        for key, value in raw.items():
            if key is None:
                continue
            row[key.strip().lower()] = (value or "").strip()
        if not any(row.values()):
            continue
        try:
            when = parse_date(row["date"])
            amount = parse_amount(row["amount"])
        except ValueError as exc:
            errors.append(f"Line {line_no}: {exc}")
            continue

        kind = Transaction.INCOME if amount > 0 else Transaction.EXPENSE
        category = categories.get(row.get("category", "").lower())
        if category is not None and category.kind != kind:
            category = None
        rows.append(
            {
                "date": when,
                "amount": abs(amount),
                "kind": kind,
                "description": row["description"][:200],
                "category": category,
            }
        )
    return rows, errors
