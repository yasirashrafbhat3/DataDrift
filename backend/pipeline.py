from __future__ import annotations

import csv
import io
import math
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

REQUIRED_COLUMNS = [
    "order_id",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "total_amount",
    "order_date",
    "customer_id",
]

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y-%m-%d %H:%M:%S",
)


def _normalize_key(value: Any) -> str:
    if value is None:
        return ""
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = _clean_text(value).replace("$", "").replace(",", "")
    if text == "":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(value: Any) -> datetime | None:
    text = _clean_text(value)
    if not text:
        return None

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def build_sample_csv() -> str:
    sample_rows = [
        {
            "order_id": "ORD-1001",
            "product_name": "Premium, Wireless Mouse",
            "category": "Electronics",
            "quantity": "2",
            "unit_price": "29.99",
            "total_amount": "59.98",
            "order_date": "2024-01-12",
            "customer_id": "CUST-101",
        },
        {
            "order_id": "ORD-1002",
            "product_name": "Classic Office Chair",
            "category": "Furniture",
            "quantity": "1",
            "unit_price": "149.00",
            "total_amount": "149.00",
            "order_date": "2024-01-15",
            "customer_id": "CUST-102",
        },
        {
            "order_id": "ORD-1003",
            "product_name": "", 
            "category": "Electronics",
            "quantity": "4",
            "unit_price": "24.50",
            "total_amount": "98.00",
            "order_date": "2024-01-18",
            "customer_id": "CUST-103",
        },
        {
            "order_id": "ORD-1004",
            "product_name": "Ergonomic Keyboard",
            "category": "Electronics",
            "quantity": "0",
            "unit_price": "79.95",
            "total_amount": "0.00",
            "order_date": "2024-01-20",
            "customer_id": "CUST-104",
        },
        {
            "order_id": "ORD-1005",
            "product_name": "Standing Desk",
            "category": "Furniture",
            "quantity": "1",
            "unit_price": "499.00",
            "total_amount": "750.00",
            "order_date": "2024-01-23",
            "customer_id": "CUST-105",
        },
        {
            "order_id": "ORD-1002",
            "product_name": "Classic Office Chair",
            "category": "Furniture",
            "quantity": "1",
            "unit_price": "149.00",
            "total_amount": "149.00",
            "order_date": "2024-01-15",
            "customer_id": "CUST-102",
        },
        {
            "order_id": "ORD-1006",
            "product_name": "Notebook Set",
            "category": "Office Supplies",
            "quantity": "10",
            "unit_price": "8.75",
            "total_amount": "87.50",
            "order_date": "invalid-date",
            "customer_id": "CUST-106",
        },
        {
            "order_id": "ORD-1007",
            "product_name": "USB-C Hub",
            "category": "Electronics",
            "quantity": "3",
            "unit_price": "99.99",
            "total_amount": "299.97",
            "order_date": "2024-02-02",
            "customer_id": "CUST-107",
        },
        {
            "order_id": "ORD-1008",
            "product_name": "Monitor Arm",
            "category": "Accessories",
            "quantity": "2",
            "unit_price": "120.00",
            "total_amount": "275.00",
            "order_date": "2024-02-09",
            "customer_id": "CUST-108",
        },
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REQUIRED_COLUMNS)
    writer.writeheader()
    writer.writerows(sample_rows)
    return output.getvalue()


def parse_csv_to_rows(csv_text: str) -> List[Dict[str, str]]:
    if not csv_text or not csv_text.strip():
        raise ValueError("CSV file is empty.")

    text_stream = io.StringIO(csv_text)
    reader = csv.DictReader(text_stream)
    if reader.fieldnames is None:
        raise ValueError("CSV file is missing a header row.")

    normalized_headers = { _normalize_key(name): name for name in reader.fieldnames if name }
    if not normalized_headers:
        raise ValueError("CSV file does not contain readable column names.")

    rows: List[Dict[str, str]] = []
    for row in reader:
        normalized_row: Dict[str, str] = {}
        for raw_key, raw_value in row.items():
            key = _normalize_key(raw_key)
            normalized_row[key] = _clean_text(raw_value)
        rows.append(normalized_row)
    return rows


def detect_missing_values(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        for field in REQUIRED_COLUMNS:
            if _clean_text(row.get(field, "")) == "":
                issues.append({
                    "row_index": idx,
                    "field": field,
                    "level": "medium",
                    "message": f"Missing value in '{field}'.",
                })
    return issues


def detect_duplicates(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    seen: Dict[str, List[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        order_id = _clean_text(row.get("order_id", ""))
        if order_id:
            seen[order_id].append(idx)

    issues: List[Dict[str, Any]] = []
    for order_id, indexes in seen.items():
        if len(indexes) > 1:
            for idx in indexes:
                issues.append({
                    "row_index": idx,
                    "field": "order_id",
                    "level": "high",
                    "message": f"Duplicate order_id '{order_id}' found.",
                })
    return issues


def detect_invalid_quantity_and_amount(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        qty = _safe_float(row.get("quantity"))
        if qty is None:
            issues.append({
                "row_index": idx,
                "field": "quantity",
                "level": "medium",
                "message": "Quantity is missing or invalid.",
            })
        elif qty <= 0 or not float(qty).is_integer():
            issues.append({
                "row_index": idx,
                "field": "quantity",
                "level": "high",
                "message": f"Quantity '{row.get('quantity')}' is invalid; expected a positive whole number.",
            })

        unit_price = _safe_float(row.get("unit_price"))
        total_amount = _safe_float(row.get("total_amount"))
        if unit_price is not None and unit_price < 0:
            issues.append({
                "row_index": idx,
                "field": "unit_price",
                "level": "high",
                "message": "Unit price cannot be negative.",
            })

        if total_amount is None:
            issues.append({
                "row_index": idx,
                "field": "total_amount",
                "level": "medium",
                "message": "Total amount is missing or invalid.",
            })
        elif total_amount <= 0:
            issues.append({
                "row_index": idx,
                "field": "total_amount",
                "level": "high",
                "message": "Total amount must be greater than zero.",
            })

        if qty is not None and unit_price is not None and total_amount is not None:
            expected = round(qty * unit_price, 2)
            if abs(expected - total_amount) > 0.01:
                issues.append({
                    "row_index": idx,
                    "field": "total_amount",
                    "level": "medium",
                    "message": (
                        f"Total amount '{total_amount}' does not match quantity x unit_price ({expected:.2f})."
                    ),
                })

    return issues


def detect_invalid_dates(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for idx, row in enumerate(rows):
        order_date = _clean_text(row.get("order_date", ""))
        if not order_date:
            issues.append({
                "row_index": idx,
                "field": "order_date",
                "level": "medium",
                "message": "Order date is missing.",
            })
            continue

        parsed = _parse_date(order_date)
        if parsed is None:
            issues.append({
                "row_index": idx,
                "field": "order_date",
                "level": "high",
                "message": f"Order date '{order_date}' is not in a supported format.",
            })
    return issues


def build_safe_cleaning_suggestions(rows: List[Dict[str, str]], issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    row_lookup: Dict[int, Dict[str, str]] = {idx: row for idx, row in enumerate(rows)}

    for issue in issues:
        row_index = issue.get("row_index")
        field = issue.get("field")
        if row_index is None or field is None:
            continue

        row = row_lookup.get(row_index, {})
        current_value = row.get(field, "")
        suggestion: Dict[str, Any] = {
            "row_index": row_index,
            "field": field,
            "original_value": current_value,
            "reason": issue.get("message", "Review this value."),
            "safe": True,
        }

        mapped = {
            "product_name": "Unknown Product",
            "category": "General",
            "quantity": 1,
            "unit_price": 0.0,
            "total_amount": 0.0,
            "customer_id": "UNKNOWN",
            "order_date": "manual review required",
        }

        if field == "total_amount":
            qty = _safe_float(row.get("quantity"))
            unit_price = _safe_float(row.get("unit_price"))
            if qty is not None and unit_price is not None:
                suggestion["suggested_value"] = round(qty * unit_price, 2)
            else:
                suggestion["suggested_value"] = 0.0
                suggestion["safe"] = False
        elif field in mapped:
            suggestion["suggested_value"] = mapped[field]
            if field in {"order_date", "product_name"} and current_value == "":
                suggestion["safe"] = False
        elif field == "order_id":
            suggestion["suggested_value"] = f"{current_value}-reviewed"
            suggestion["safe"] = False
        else:
            suggestion["suggested_value"] = current_value
            suggestion["safe"] = False

        if issue.get("level") == "high" and field in {"quantity", "total_amount", "order_date"}:
            suggestion["safe"] = False

        suggestions.append(suggestion)

    return suggestions


def data_quality_score(rows: List[Dict[str, str]], issues: List[Dict[str, Any]]) -> int:
    if not rows:
        return 100

    penalty = 0
    for issue in issues:
        severity_weight = {"high": 12, "medium": 5, "low": 2}.get(issue.get("level", "low"), 2)
        penalty += severity_weight

    penalty = min(penalty, 100)
    return max(0, 100 - penalty)


def calculate_analytics(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    valid_rows = [row for row in rows if row]
    if not valid_rows:
        return {
            "total_orders": 0,
            "total_revenue": 0.0,
            "average_order_value": 0.0,
            "unique_customers": 0,
            "top_category": "N/A",
            "top_product": "N/A",
            "monthly_trend": [],
        }

    revenue = 0.0
    category_totals: Dict[str, float] = defaultdict(float)
    product_totals: Dict[str, float] = defaultdict(float)
    customer_ids = set()
    for row in valid_rows:
        customer_id = _clean_text(row.get("customer_id", ""))
        if customer_id:
            customer_ids.add(customer_id)

        amount = _safe_float(row.get("total_amount"))
        if amount is not None:
            revenue += amount

        category = _clean_text(row.get("category", "Unknown"))
        category_totals[category] += amount or 0.0

        product_name = _clean_text(row.get("product_name", "Unknown Product"))
        product_totals[product_name] += amount or 0.0

    top_category = max(category_totals.items(), key=lambda item: item[1], default=("N/A", 0.0))[0]
    top_product = max(product_totals.items(), key=lambda item: item[1], default=("N/A", 0.0))[0]

    monthly_trend: List[Dict[str, Any]] = []
    dates_by_month: Dict[str, float] = defaultdict(float)
    for row in valid_rows:
        order_date = _parse_date(row.get("order_date"))
        if order_date is None:
            continue
        month_key = order_date.strftime("%Y-%m")
        dates_by_month[month_key] += _safe_float(row.get("total_amount")) or 0.0

    for key, total in sorted(dates_by_month.items()):
        monthly_trend.append({"month": key, "revenue": round(total, 2)})

    return {
        "total_orders": len(valid_rows),
        "total_revenue": round(revenue, 2),
        "average_order_value": round(revenue / len(valid_rows), 2) if valid_rows else 0.0,
        "unique_customers": len(customer_ids),
        "top_category": top_category,
        "top_product": top_product,
        "monthly_trend": monthly_trend,
    }


def detect_anomalies(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    anomalies: List[Dict[str, Any]] = []
    qty_values = []
    amount_values = []

    for idx, row in enumerate(rows):
        qty = _safe_float(row.get("quantity"))
        amount = _safe_float(row.get("total_amount"))
        if qty is not None:
            qty_values.append((idx, qty))
        if amount is not None:
            amount_values.append((idx, amount))

    if qty_values:
        qty_list = [value for _, value in qty_values]
        qty_median = sorted(qty_list)[len(qty_list) // 2]
        for idx, qty in qty_values:
            if qty > qty_median * 3:
                anomalies.append({
                    "row_index": idx,
                    "field": "quantity",
                    "type": "Quantity spike",
                    "message": f"Quantity {qty} is unusually high compared to the median value.",
                })

    if amount_values:
        amounts = [value for _, value in amount_values]
        median = sorted(amounts)[len(amounts) // 2]
        for idx, amount in amount_values:
            if amount > median * 3:
                anomalies.append({
                    "row_index": idx,
                    "field": "total_amount",
                    "type": "Revenue anomaly",
                    "message": f"Order total ${amount:.2f} is unusually large versus the dataset median.",
                })

    return anomalies


def analyze_csv_text(csv_text: str, file_name: str = "upload.csv") -> Dict[str, Any]:
    rows = parse_csv_to_rows(csv_text)

    missing_issues = detect_missing_values(rows)
    duplicate_issues = detect_duplicates(rows)
    qty_issues = detect_invalid_quantity_and_amount(rows)
    date_issues = detect_invalid_dates(rows)
    all_issues = missing_issues + duplicate_issues + qty_issues + date_issues

    suggestions = build_safe_cleaning_suggestions(rows, all_issues)
    quality = data_quality_score(rows, all_issues)
    analytics = calculate_analytics(rows)
    anomalies = detect_anomalies(rows)

    return {
        "file_name": file_name,
        "row_count": len(rows),
        "quality_score": quality,
        "issues": all_issues,
        "suggestions": suggestions,
        "analytics": analytics,
        "anomalies": anomalies,
        "rows": rows,
        "required_columns": REQUIRED_COLUMNS,
    }


def apply_approved_changes(rows: List[Dict[str, str]], approved_changes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    working_rows = [dict(row) for row in rows]
    for change in approved_changes:
        row_index = change.get("row_index")
        field = change.get("field")
        if row_index is None or field is None:
            continue
        if row_index < 0 or row_index >= len(working_rows):
            continue
        if field not in working_rows[row_index]:
            continue

        new_value = change.get("suggested_value")
        if new_value is None:
            continue

        if field in {"quantity", "unit_price", "total_amount"}:
            if isinstance(new_value, (int, float)):
                working_rows[row_index][field] = str(new_value)
            else:
                working_rows[row_index][field] = str(new_value)
        else:
            working_rows[row_index][field] = str(new_value)

    return working_rows


def export_rows_as_csv(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REQUIRED_COLUMNS)
    writer.writeheader()
    for row in rows:
        cleaned = {column: row.get(column, "") for column in REQUIRED_COLUMNS}
        writer.writerow(cleaned)
    return output.getvalue()
