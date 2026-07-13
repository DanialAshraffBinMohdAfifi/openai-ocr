TOLERANCE = 0.05


def validate_receipt_data(data):
    warnings = []

    has_vendor_name = bool(data.get("vendor_name"))
    has_receipt_date = bool(data.get("receipt_date"))
    has_receipt_or_reference_number = bool(data.get("receipt_number") or data.get("reference_number"))
    has_total_amount = _is_number(data.get("total_amount"))

    if not has_vendor_name:
        warnings.append("Vendor name is missing.")
    if not has_receipt_date:
        warnings.append("Receipt date is missing.")
    if not has_receipt_or_reference_number:
        warnings.append("Receipt number and reference number are missing.")
    if not has_total_amount:
        warnings.append("Total amount is missing or not numeric.")
    if data.get("tax_sst_amount") is not None and not _is_number(data.get("tax_sst_amount")):
        warnings.append("Tax/SST amount is present but not numeric.")

    items_total_check = _validate_items(data.get("items", []), data.get("total_amount"), warnings)

    model_warnings = data.get("warnings")
    if isinstance(model_warnings, list):
        warnings.extend(str(warning) for warning in model_warnings if warning)

    return {
        "has_vendor_name": has_vendor_name,
        "has_receipt_date": has_receipt_date,
        "has_receipt_or_reference_number": has_receipt_or_reference_number,
        "has_total_amount": has_total_amount,
        "items_total_check": items_total_check,
        "warnings": warnings,
    }


def _validate_items(items, total_amount, warnings):
    if not isinstance(items, list) or not items:
        warnings.append("No item rows were extracted.")
        return False

    check_passed = True
    line_totals = []

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            warnings.append(f"Item {index} is not a valid object.")
            check_passed = False
            continue

        quantity = item.get("quantity")
        amount = item.get("amount")
        line_total = item.get("total")

        if _is_number(quantity) and _is_number(amount) and _is_number(line_total):
            expected_total = float(quantity) * float(amount)
            if abs(expected_total - float(line_total)) > TOLERANCE:
                warnings.append(f"Item {index} quantity x amount does not match line total.")
                check_passed = False

        if _is_number(line_total):
            line_totals.append(float(line_total))

    if line_totals and _is_number(total_amount):
        summed_items = sum(line_totals)
        if abs(summed_items - float(total_amount)) > max(TOLERANCE, float(total_amount) * 0.02):
            warnings.append("Sum of item totals does not roughly match receipt total.")
            check_passed = False

    return check_passed


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
