TOLERANCE = 0.05


def validate_receipt_data(payload):
    document_type = payload.get("document_type") if isinstance(payload, dict) else "unknown"
    data = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else {}
    warnings = []

    if document_type == "receipt":
        checks = _validate_receipt(data, warnings)
    elif document_type == "invoice":
        checks = _validate_invoice(data, warnings)
    elif document_type == "payment_receipt":
        checks = _validate_payment_receipt(data, warnings)
    elif document_type == "delivery_order":
        checks = _validate_delivery_order(data, warnings)
    else:
        document_type = "unknown"
        checks = _validate_unknown(data, warnings)

    model_warnings = payload.get("warnings") if isinstance(payload, dict) else None
    if isinstance(model_warnings, list):
        warnings.extend(str(warning) for warning in model_warnings if warning)
    warnings = _dedupe(warnings)

    required_fields_check = checks["required_fields_check"]
    items_total_check = checks["items_total_check"]
    total_breakdown_check = checks["total_breakdown_check"]

    return {
        "document_type": document_type,
        "valid_for_document_type": required_fields_check is not False
        and items_total_check is not False
        and total_breakdown_check is not False,
        "required_fields_check": required_fields_check,
        "items_total_check": items_total_check,
        "total_breakdown_check": total_breakdown_check,
        "warnings": warnings,
    }


def _validate_receipt(data, warnings):
    has_vendor_name = _require_bool(data.get("vendor_name"), "Vendor name is missing.", warnings)
    has_receipt_date = _require_bool(data.get("receipt_date"), "Receipt date is missing.", warnings)
    has_number = _require_bool(data.get("receipt_number"), "Receipt number is missing.", warnings)
    has_total = _require_number(data.get("total_amount"), "Total amount is missing or not numeric.", warnings)
    has_currency = _require_bool(data.get("currency"), "Currency is missing.", warnings)

    _warn_non_numeric_breakdown(data, warnings, ("subtotal", "tax_sst_amount"))
    items_total_check = _validate_items(data.get("items", []), data.get("subtotal") if _is_number(data.get("subtotal")) else data.get("total_amount"), "receipt subtotal or total", warnings)
    total_breakdown_check = _validate_total_breakdown(
        data,
        "total_amount",
        warnings,
        add_fields=("tax_sst_amount",),
        subtract_fields=(),
        gentle=True,
    )

    return {
        "required_fields_check": has_vendor_name and has_receipt_date and has_number and has_total and has_currency,
        "items_total_check": items_total_check,
        "total_breakdown_check": total_breakdown_check,
    }


def _validate_invoice(data, warnings):
    has_vendor_name = _require_bool(data.get("vendor_name"), "Vendor name is missing.", warnings)
    has_customer_name = _require_bool(data.get("customer_name"), "Customer name is missing.", warnings)
    has_number = _require_bool(data.get("invoice_number"), "Invoice number is missing.", warnings)
    has_date = _require_bool(data.get("invoice_date"), "Invoice date is missing.", warnings)
    has_total = _require_number(data.get("total_amount"), "Total amount is missing or not numeric.", warnings)
    has_currency = _require_bool(data.get("currency"), "Currency is missing.", warnings)

    _warn_non_numeric_breakdown(data, warnings, ("subtotal", "tax_sst_amount"))
    items_total_check = _validate_items(data.get("items", []), data.get("subtotal") if _is_number(data.get("subtotal")) else data.get("total_amount"), "invoice subtotal or total", warnings)
    total_breakdown_check = _validate_total_breakdown(
        data,
        "total_amount",
        warnings,
        add_fields=("tax_sst_amount",),
        subtract_fields=(),
        gentle=True,
    )

    return {
        "required_fields_check": has_vendor_name and has_customer_name and has_number and has_date and has_total and has_currency,
        "items_total_check": items_total_check,
        "total_breakdown_check": total_breakdown_check,
    }


def _validate_payment_receipt(data, warnings):
    has_vendor_name = _require_bool(data.get("vendor_name"), "Vendor name is missing.", warnings)
    has_payer_name = _require_bool(data.get("payer_name"), "Payer name is missing.", warnings)
    has_number = _require_bool(
        data.get("receipt_number") or data.get("reference_number"),
        "Receipt number and reference number are missing.",
        warnings,
    )
    has_date = _require_bool(data.get("payment_date"), "Payment date is missing.", warnings)
    has_total = _require_number(
        data.get("total_amount_received"),
        "Total amount received is missing or not numeric.",
        warnings,
    )
    has_currency = _require_bool(data.get("currency"), "Currency is missing.", warnings)

    items_total_check = _validate_items(data.get("items", []), data.get("total_amount_received"), "total amount received", warnings)

    return {
        "required_fields_check": has_vendor_name and has_payer_name and has_number and has_date and has_total and has_currency,
        "items_total_check": items_total_check,
        "total_breakdown_check": None,
    }


def _validate_delivery_order(data, warnings):
    has_vendor_name = _require_bool(data.get("vendor_name"), "Vendor name is missing.", warnings)
    has_number = _require_bool(
        data.get("delivery_order_number"),
        "Delivery order number is missing.",
        warnings,
    )
    has_date = _require_bool(data.get("delivery_date"), "Delivery date is missing.", warnings)
    has_recipient = _require_bool(
        data.get("customer_name") or data.get("deliver_to"),
        "Customer name and deliver-to fields are missing.",
        warnings,
    )

    items = data.get("items")
    items_total_check = True
    if not isinstance(items, list) or not items:
        warnings.append("No delivery item rows were extracted.")
        items_total_check = False

    return {
        "required_fields_check": has_vendor_name and has_number and has_date and has_recipient,
        "items_total_check": items_total_check,
        "total_breakdown_check": None,
    }


def _validate_unknown(data, warnings):
    _append_unique(warnings, "Document type is unknown. Please review manually.")
    items_total_check = _validate_unknown_items(data.get("items"), warnings)
    return {
        "required_fields_check": False,
        "items_total_check": items_total_check,
        "total_breakdown_check": None,
    }


def _validate_unknown_items(items, warnings):
    if not isinstance(items, list) or not items:
        return None

    check_passed = True
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            warnings.append(f"Unknown item {index} is not a valid object.")
            check_passed = False
            continue

        quantity = item.get("quantity")
        unit_price = item.get("unit_price")
        line_total = item.get("line_total")

        if _is_number(quantity) and _is_number(unit_price) and _is_number(line_total):
            expected_total = float(quantity) * float(unit_price)
            if abs(expected_total - float(line_total)) > TOLERANCE:
                warnings.append(f"Unknown item {index} quantity x unit price does not match line total.")
                check_passed = False

    return False if not check_passed else None


def _validate_total_breakdown(data, total_field, warnings, add_fields, subtract_fields, gentle=False):
    subtotal = data.get("subtotal")
    total_amount = data.get(total_field)

    if not _is_number(subtotal) or not _is_number(total_amount):
        return None

    expected_total = float(subtotal)
    for field_name in add_fields:
        expected_total += _number_or_zero(data.get(field_name))
    for field_name in subtract_fields:
        expected_total -= _number_or_zero(data.get(field_name))

    actual_total = float(total_amount)
    allowed_difference = max(0.10, abs(actual_total) * 0.02)

    if abs(expected_total - actual_total) > allowed_difference:
        suffix = " Some adjustments may not be extracted in the simplified schema." if gentle else ""
        warnings.append(f"Total breakdown mismatch: calculated total is {expected_total:.2f}, but document total is {actual_total:.2f}.{suffix}")
        return False

    return True


def _validate_items(items, comparison_total, comparison_label, warnings):
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
        unit_price = item.get("unit_price")
        line_total = item.get("line_total")

        if _is_number(quantity) and _is_number(unit_price) and _is_number(line_total):
            expected_total = float(quantity) * float(unit_price)
            if abs(expected_total - float(line_total)) > TOLERANCE:
                warnings.append(f"Item {index} quantity x unit price does not match line total.")
                check_passed = False

        if _is_number(line_total):
            line_totals.append(float(line_total))

    if line_totals and _is_number(comparison_total):
        summed_items = sum(line_totals)
        if abs(summed_items - float(comparison_total)) > max(TOLERANCE, abs(float(comparison_total)) * 0.02):
            warnings.append(f"Sum of item totals does not roughly match {comparison_label}.")
            check_passed = False

    return check_passed


def _warn_non_numeric_breakdown(data, warnings, field_names):
    labels = {
        "subtotal": "Subtotal",
        "tax_sst_amount": "Tax/SST amount",
    }
    for field_name in field_names:
        if data.get(field_name) is not None and not _is_number(data.get(field_name)):
            warnings.append(f"{labels.get(field_name, field_name)} is present but not numeric.")


def _require_bool(value, warning, warnings):
    exists = bool(value)
    if not exists:
        warnings.append(warning)
    return exists


def _require_number(value, warning, warnings):
    exists = _is_number(value)
    if not exists:
        warnings.append(warning)
    return exists


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _number_or_zero(value):
    return float(value) if _is_number(value) else 0.0


def _append_unique(items, value):
    if value not in items:
        items.append(value)


def _dedupe(items):
    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
