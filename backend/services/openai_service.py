import json
import os

from openai import OpenAI, OpenAIError

from prompts.receipt_prompt import RECEIPT_PROMPT, RECEIPT_SCHEMA
from services.cost_service import calculate_openai_cost, safe_get_token_usage


class OpenAIExtractionError(Exception):
    pass


def extract_receipt_data(image_data_url):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise OpenAIExtractionError(
            "OpenAI API key is not configured. Please create backend/.env based on "
            "backend/.env.example and set OPENAI_API_KEY."
        )

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

    try:
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": RECEIPT_PROMPT},
                        {"type": "input_image", "image_url": image_data_url},
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "receipt_extraction",
                    "schema": RECEIPT_SCHEMA,
                    "strict": True,
                }
            },
        )
    except OpenAIError as exc:
        raise OpenAIExtractionError("OpenAI extraction request failed.") from exc

    raw_text = getattr(response, "output_text", None)
    if not raw_text:
        raise OpenAIExtractionError("OpenAI returned an empty response.")

    token_usage = safe_get_token_usage(response)
    cost_data = calculate_openai_cost(token_usage, model)

    return _parse_json(raw_text), cost_data


def _parse_json(raw_text):
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise OpenAIExtractionError("OpenAI returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise OpenAIExtractionError("OpenAI response JSON must be an object.")

    return parsed
