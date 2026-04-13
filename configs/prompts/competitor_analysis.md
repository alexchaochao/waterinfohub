Analyze a competitor news item for smart water market intelligence.

Rules:

- Output valid JSON only.
- Separate facts from analysis.
- Keep impact_analysis within two sentences.
- Use null for unknown values.

JSON schema:

{
  "company_name": "string | null",
  "event_type": "new_product | market_expansion | certification | award | technology_upgrade | strategic_partnership | investment | null",
  "technologies": ["string"],
  "market": "string | null",
  "products": ["string"],
  "strategic_intent": "string | null",
  "impact_analysis": "string | null",
  "signal_strength": 0.0
}
