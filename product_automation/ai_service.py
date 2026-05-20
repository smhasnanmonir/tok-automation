"""
AI Service for TOK Product Automation.
Generates product details using OpenRouter API.
"""

import json
import time
from typing import Any

import requests
from config import config


class AIError(Exception):
    """Custom exception for AI API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def generate_product_details(
    product_name: str,
) -> dict[str, Any]:
    """
    Generate product details using OpenRouter AI.

    Args:
        product_name: The name of the product

    Returns:
        Dictionary with product details:
        - origin_country: str
        - stock: bool
        - expiry_date: str
        - description: str
        - key_ingredient: str
        - how_to_use: list[str]
        - benefits: list[str]
        - skin_type: str
        - skin_concern: str
        - sizes: list[str]
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://tokbd.com",
        "X-Title": "TOK Product Automation",
    }

    # Build the prompt
    prompt = f"""
You are an expert SEO copywriter and skincare/beauty product specialist.
Generate highly optimized, realistic product information for the product: "{product_name}"

CRITICAL TONE AND STYLE GUIDELINES:
1. SEO is the absolute main priority. Sprinkle primary and secondary keywords naturally throughout the description and benefits.
2. Keep the language simple, relatable, and easy to read.
3. The text MUST have a human-friendly, conversational tone. Do not sound like a robot.
4. ABSOLUTELY NO EMOJIS and NO DASHES (--) in your response.
5. If writing in or translating any phrases to Bengali, it MUST be 100% natural, colloquial, and native-sounding. Forbid unnatural, literal, or robotic Bengali translations entirely.

Generate a JSON object with these exact fields:
{generate_product_prompt()}

CRITICAL RULES:
- Do NOT include "price", retail price, or BDT selling price in the JSON. The shop selling price is always entered manually by staff; never estimate or invent it.
- Respond with ONLY valid JSON. No markdown, no code blocks, no explanations.
"""

    # Make the API call
    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.7,
        "max_tokens": 4096,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Clean up markdown code fence markers
        cleaned = content.strip()
        cleaned = cleaned.replace("```json", "").replace("```", "")
        cleaned = cleaned.strip()

        # Parse JSON
        product_data = json.loads(cleaned)

        # Convert to the expected format
        return parse_product_data(product_data)

    except requests.exceptions.RequestException as e:
        print(f"  ⚠ AI API error: {e}")
        raise AIError(f"Failed to call OpenRouter API: {e}")
    except json.JSONDecodeError as e:
        print(f"  ⚠ Failed to parse AI response: {e}")
        raise AIError("Failed to parse AI response. The API may have returned invalid JSON.")
    except Exception as e:
        print(f"  ⚠ Unexpected error during AI generation: {e}")
        raise AIError(f"Unexpected error: {e}")


def generate_product_prompt() -> str:
    """
    Generate the prompt template for product details.
    """
    return """
{
  "origin_country": "Country of origin. If South Korea, MUST return 'korea' (lowercase). For others, use standard name.",
  "stock": true,
  "expiry_date": "Upto 2028",
  "description": "A detailed product description with MINIMUM 5 sentences. Include what the product does, key benefits, who it's for, how it works, and why it's effective.",
  "key_ingredient": "Main active ingredient(s)",
  "how_to_use": ["Step 1 instruction", "Step 2 instruction", "Step 3 instruction"],
  "benefits": ["Benefit 1", "Benefit 2", "Benefit 3", "Benefit 4"],
  "skin_type": "MUST be exactly one of: Acne, Combination, Damaged, Dry, Oily, Sensitive. If not match exactly insert new values. Can be multiple separated by commas, but prioritize listed values if they match.",
  "skin_concern": "MUST use ONLY values from this prioritized list: Acne, Aging, Brightening, Sunburn, B&W Heads, Dark Circle, Dehydration, Redness, Pigmentation, Oily. If not match exactly insert new values, You may include multiple separated by commas, but only use the listed values.",
  "sizes": ["Extract size value ONLY (no units) from product name. E.g. for '30ml' return '30'. Return as string."]
}
"""


def parse_product_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Parse and convert AI response to the expected format.
    """
    result: dict[str, Any] = {}

    # String fields
    string_fields = [
        "origin_country",
        "expiry_date",
        "description",
        "key_ingredient",
    ]
    for field in string_fields:
        if field in raw_data:
            result[field] = str(raw_data[field]).strip() if raw_data[field] else ""

    # Boolean field
    if "stock" in raw_data:
        result["stock"] = bool(raw_data["stock"])

    # Array fields
    array_fields = ["how_to_use", "benefits", "skin_type", "skin_concern", "sizes"]
    for field in array_fields:
        if field in raw_data:
            val = raw_data[field]
            if isinstance(val, list):
                result[field] = [str(v) for v in val if v]
            elif isinstance(val, str):
                # Handle comma-separated values
                result[field] = [v.strip() for v in val.split(",") if v.strip()]
            else:
                result[field] = []

    # Default values if missing
    if not result.get("origin_country"):
        result["origin_country"] = "korea"

    if not result.get("stock"):
        result["stock"] = True

    if not result.get("expiry_date"):
        result["expiry_date"] = "Upto 2028"

    if not result.get("description"):
        result["description"] = ""

    if not result.get("key_ingredient"):
        result["key_ingredient"] = ""

    if not result.get("how_to_use"):
        result["how_to_use"] = ["Cleanse skin", "Apply product", "Massage gently", "Wait for absorption"]

    if not result.get("benefits"):
        result["benefits"] = ["Provides hydration", "Improves skin texture", "Enhances glow", "Protects skin"]

    if not result.get("skin_type"):
        result["skin_type"] = "All"

    if not result.get("skin_concern"):
        result["skin_concern"] = "All"

    if not result.get("sizes"):
        result["sizes"] = ["1"]

    return result
