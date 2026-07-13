import os


DEFAULT_INPUT_COST_PER_1M = 0.25
DEFAULT_OUTPUT_COST_PER_1M = 2.00
DEFAULT_USD_TO_MYR_RATE = 4.70


def safe_get_token_usage(response):
    usage = getattr(response, "usage", None)
    if usage is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "warning": "Token usage was not available from the OpenAI response.",
        }

    input_tokens = _get_usage_value(usage, "input_tokens", "prompt_tokens")
    output_tokens = _get_usage_value(usage, "output_tokens", "completion_tokens")
    total_tokens = _get_usage_value(usage, "total_tokens")

    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens

    token_usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }

    if input_tokens == 0 and output_tokens == 0 and total_tokens == 0:
        token_usage["warning"] = "Token usage was not available from the OpenAI response."

    return token_usage


def calculate_openai_cost(usage, model):
    input_price = _get_float_env("OPENAI_INPUT_COST_PER_1M", DEFAULT_INPUT_COST_PER_1M)
    output_price = _get_float_env("OPENAI_OUTPUT_COST_PER_1M", DEFAULT_OUTPUT_COST_PER_1M)
    usd_to_myr_rate = _get_float_env("USD_TO_MYR_RATE", DEFAULT_USD_TO_MYR_RATE)

    input_tokens = _safe_int(usage.get("input_tokens"))
    output_tokens = _safe_int(usage.get("output_tokens"))
    total_tokens = _safe_int(usage.get("total_tokens"))

    if total_tokens == 0 and (input_tokens or output_tokens):
        total_tokens = input_tokens + output_tokens

    input_cost_usd = input_tokens / 1_000_000 * input_price
    output_cost_usd = output_tokens / 1_000_000 * output_price
    total_cost_usd = input_cost_usd + output_cost_usd
    total_cost_myr = total_cost_usd * usd_to_myr_rate

    result = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_cost_usd": round(input_cost_usd, 6),
        "output_cost_usd": round(output_cost_usd, 6),
        "total_cost_usd": round(total_cost_usd, 6),
        "total_cost_myr": round(total_cost_myr, 4),
        "pricing": {
            "input_per_1m_usd": input_price,
            "output_per_1m_usd": output_price,
            "usd_to_myr_rate": usd_to_myr_rate,
        },
    }

    if usage.get("warning"):
        result["warning"] = usage["warning"]

    return result


def _get_usage_value(usage, *field_names):
    for field_name in field_names:
        value = _get_field(usage, field_name)
        if value is not None:
            return _safe_int(value)
    return 0


def _get_field(source, field_name):
    if isinstance(source, dict):
        return source.get(field_name)
    return getattr(source, field_name, None)


def _get_float_env(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
