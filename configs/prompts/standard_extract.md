Extract a single standards or regulation event from the input text.

Rules:

- Output valid JSON only.
- Do not invent dates, identifiers, or organizations.
- Use null for any unknown field.
- Keep relevance_reason short and factual.

JSON schema:

{
  "standard_name": "string | null",
  "standard_no": "string | null",
  "device_type": "water_meter | electricity_meter | gas_meter | communication_protocol | metrology | null",
  "action_type": "new | update | withdrawn | consultation | null",
  "organization": "string | null",
  "region": "string | null",
  "published_at": "ISO-8601 string | null",
  "source_url": "string | null",
  "relevance_reason": "string | null"
}
