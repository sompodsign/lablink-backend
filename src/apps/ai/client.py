"""Anthropic Claude client for AI report extraction.

Wraps the Anthropic Messages API (vision) to extract structured
diagnostic report data from photographs of lab result slips.
"""

import base64
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Default model — Haiku is fast and cheap for structured extraction
DEFAULT_MODEL = 'claude-3-5-haiku-latest'
MAX_TOKENS = 2048


EXTRACTION_PROMPT = """You are a medical laboratory data-extraction assistant.

You will be given a photograph of a diagnostic test report and a list of
expected result fields. Extract the value for each field from the image.

**Expected fields for "{test_type_name}":**
{fields_json}

**Instructions:**
1. For each expected field, find its value in the image.
2. Return ONLY valid JSON — no markdown fences, no explanation.
3. Use this exact structure:
{{
  "<field_name>": {{
    "value": "<extracted value as string>",
    "unit": "<unit from the image or from expected fields>",
    "finding": "<Normal | High | Low | Critical | null>"
  }}
}}
4. If a field is not visible in the image, set its value to "" and finding to null.
5. Compare the extracted value against the reference range (if visible) to determine the finding.
6. Preserve numeric precision exactly as shown in the image.
"""


class ExtractionResult:
    """Container for AI extraction response."""

    __slots__ = ('result_data', 'input_tokens', 'output_tokens', 'model')

    def __init__(
        self,
        result_data: dict,
        input_tokens: int,
        output_tokens: int,
        model: str,
    ):
        self.result_data = result_data
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.model = model


def extract_report_data(
    *,
    image_bytes: bytes,
    mime_type: str,
    template_fields: list[dict],
    test_type_name: str,
    model: str = DEFAULT_MODEL,
) -> ExtractionResult:
    """Send a report image to Claude and get structured result_data back.

    Args:
        image_bytes: Raw image bytes (JPEG/PNG/WebP).
        mime_type: MIME type of the image (e.g. 'image/jpeg').
        template_fields: List of field dicts from ReportTemplate.fields,
            e.g. [{"name": "Hemoglobin", "unit": "g/dL", "ref_range": "13.5-17.5"}]
        test_type_name: Human-readable test type name for the prompt.
        model: Anthropic model identifier.

    Returns:
        ExtractionResult with parsed result_data and token usage.

    Raises:
        anthropic.APIError: On API-level failures.
        ValueError: If the response cannot be parsed as JSON.
    """
    import anthropic

    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError(
            'ANTHROPIC_API_KEY is not configured. '
            'Add it to your .env file to enable AI features.'
        )

    client = anthropic.Anthropic(api_key=api_key)

    # Build the prompt with field expectations
    fields_json = json.dumps(
        [
            {
                'name': f.get('name', ''),
                'unit': f.get('unit', ''),
                'ref_range': f.get('ref_range', f.get('ref_range_male', '')),
            }
            for f in template_fields
        ],
        indent=2,
    )

    prompt_text = EXTRACTION_PROMPT.format(
        test_type_name=test_type_name,
        fields_json=fields_json,
    )

    # Encode image as base64
    image_b64 = base64.standard_b64encode(image_bytes).decode('utf-8')

    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        messages=[
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': mime_type,
                            'data': image_b64,
                        },
                    },
                    {
                        'type': 'text',
                        'text': prompt_text,
                    },
                ],
            }
        ],
    )

    # Extract text from the response
    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw_text.startswith('```'):
        lines = raw_text.split('\n')
        # Remove first and last lines (fences)
        lines = [l for l in lines if not l.strip().startswith('```')]
        raw_text = '\n'.join(lines).strip()

    try:
        result_data = json.loads(raw_text)
    except json.JSONDecodeError as err:
        logger.error(
            'Failed to parse AI response as JSON: %s',
            raw_text[:200],
        )
        raise ValueError(
            'AI returned an unparseable response. Please try again.'
        ) from err

    return ExtractionResult(
        result_data=result_data,
        input_tokens=message.usage.input_tokens,
        output_tokens=message.usage.output_tokens,
        model=model,
    )
