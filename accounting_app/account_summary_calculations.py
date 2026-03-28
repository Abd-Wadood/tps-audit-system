import json
from decimal import Decimal, InvalidOperation


LOCAL_PURCHASE_FIELDS = [
    ("cheese", "Cheese"),
    ("fries", "Fries"),
    ("burger", "Burger"),
    ("vegetables", "Vegetables"),
    ("coal", "Coal"),
    ("eggs", "Eggs"),
    ("petrol", "Petrol"),
    ("local_demand", "Local Demand"),
    ("local_spend", "Local Spend"),
    ("flour", "Flour"),
    ("mayo", "Mayo"),
    ("gas", "Gas"),
    ("coke_bulk", "Coke Bulk"),
    ("delivery", "Delivery"),
    ("maintenance", "Maintenance"),
]

MARKET_PURCHASE_FIELDS = [
    ("chicken", "Chicken"),
    ("sheikh_bill", "Sheikh Bill"),
    ("packing", "Packing"),
    ("nuggets", "Nuggets"),
    ("patties", "Patties"),
]

COUNTER_SUMMARY_FIELDS = [
    ("counter_sale", "Counter Sale"),
    ("direct_sale", "Direct Sale"),
    ("credit", "Credit (Udhar Wapis)"),
]

TOTAL_SUMMARY_FIELDS = [
    ("loan", "Loan"),
    ("extra_fee", "Extra Fee"),
    ("total_wage", "Total Wage"),
    ("food_panda", "Food Panda"),
    ("discount", "Discount"),
    ("counter_purchase", "Counter Purchase"),
]

SECTION_CONFIG = {
    "local": {
        "title": "Local Purchases",
        "fields": LOCAL_PURCHASE_FIELDS,
        "total_key": "total_local_purchase",
        "total_label": "Total Local Purchase",
    },
    "market": {
        "title": "Market Purchase",
        "fields": MARKET_PURCHASE_FIELDS,
        "total_key": "total_market_purchase",
        "total_label": "Total Market Purchase",
    },
    "counter": {
        "title": "Counter Summary",
        "fields": COUNTER_SUMMARY_FIELDS,
        "total_key": "counter_sale_total",
        "total_label": "Total Sale",
    },
    "total": {
        "title": "Total Summary Purchases",
        "fields": TOTAL_SUMMARY_FIELDS,
        "total_key": "adjustment_total",
        "total_label": "Total Summary Purchase",
    },
}


def parse_decimal(value, *, clamp_non_negative=False):
    if value in (None, ""):
        return Decimal("0")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    if clamp_non_negative and parsed < 0:
        return Decimal("0")
    return parsed


def extract_section(post_data, section_name):
    config = SECTION_CONFIG[section_name]
    values = {key: str(parse_decimal(post_data.get(f"{section_name}_{key}", "0"), clamp_non_negative=True)) for key, _ in config["fields"]}

    raw_custom = post_data.get(f"{section_name}_custom_rows", "[]")
    try:
        decoded = json.loads(raw_custom)
    except json.JSONDecodeError:
        decoded = []

    custom_rows = []
    for row in decoded:
        label = str(row.get("label", "")).strip()
        if not label:
            continue
        amount = parse_decimal(row.get("value", "0"), clamp_non_negative=True)
        custom_rows.append({"label": label, "value": str(amount)})

    return {"values": values, "custom_rows": custom_rows}


def sum_section(section):
    base_total = sum(parse_decimal(value, clamp_non_negative=True) for value in section.get("values", {}).values())
    custom_total = sum(parse_decimal(row.get("value"), clamp_non_negative=True) for row in section.get("custom_rows", []))
    return base_total + custom_total


def calculate_totals(system_sale, local_data, market_data, counter_data, total_data):
    total_local_purchase = sum_section(local_data)
    total_market_purchase = sum_section(market_data)
    counter_sale = parse_decimal(counter_data["values"].get("counter_sale"), clamp_non_negative=True)
    direct_sale = parse_decimal(counter_data["values"].get("direct_sale"), clamp_non_negative=True)
    credit = parse_decimal(counter_data["values"].get("credit"), clamp_non_negative=True)

    loan = parse_decimal(total_data["values"].get("loan"), clamp_non_negative=True)
    extra_fee = parse_decimal(total_data["values"].get("extra_fee"), clamp_non_negative=True)
    total_wage = parse_decimal(total_data["values"].get("total_wage"), clamp_non_negative=True)
    food_panda = parse_decimal(total_data["values"].get("food_panda"), clamp_non_negative=True)
    discount = parse_decimal(total_data["values"].get("discount"), clamp_non_negative=True)
    counter_purchase = parse_decimal(total_data["values"].get("counter_purchase"), clamp_non_negative=True)
    custom_total_adjustments = sum(
        parse_decimal(row.get("value"), clamp_non_negative=True) for row in total_data.get("custom_rows", [])
    )

    system_sale_value = parse_decimal(system_sale, clamp_non_negative=True)
    total_sale = counter_sale + direct_sale
    total_purchase = total_local_purchase + total_market_purchase + (
        loan + extra_fee + total_wage + counter_purchase + custom_total_adjustments + discount
    )
    difference = counter_sale - system_sale_value
    balance = total_sale - total_purchase

    return {
        "system_sale": system_sale_value,
        "counter_sale": counter_sale,
        "direct_sale": direct_sale,
        "credit": credit,
        "total_sale": total_sale,
        "total_local_purchase": total_local_purchase,
        "total_market_purchase": total_market_purchase,
        "total_purchase": total_purchase,
        "difference": difference,
        "balance": balance,
        "loan": loan,
        "extra_fee": extra_fee,
        "total_wage": total_wage,
        "food_panda": food_panda,
        "discount": discount,
        "counter_purchase": counter_purchase,
        "custom_total_adjustments": custom_total_adjustments,
        "adjustment_total": loan + extra_fee + total_wage + counter_purchase + custom_total_adjustments + discount,
    }
