# json_parser.py
import json
import re
from typing import Any

def fix_json_from_ai(text: str) -> str:
    """Attempt to fix/clean JSON from AI output."""
    # Remove Markdown code block wrappers
    text = re.sub(r'```(json)?', '', text).strip()
    # Try to isolate JSON section if extra text/prompt is included
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        text = match.group(1)
    # Remove control characters and make best effort
    text = re.sub(r'[\x00-\x1F\x7F]', '', text)
    return text

def parse_ai_json_response(response_text: str) -> Any:
    """Safely parse AI's JSON response, with cleaning/fixing."""
    try:
        return json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        try:
            fixed = fix_json_from_ai(response_text)
            return json.loads(fixed)
        except Exception as e:
            # Optionally log error somewhere
            raise ValueError(f"Failed to parse AI JSON: {e}\nOriginal: {response_text}")
