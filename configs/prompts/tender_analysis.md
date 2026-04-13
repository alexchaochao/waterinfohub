Extract tender information from a procurement announcement.

Rules:

- Output valid JSON only.
- Do not infer monetary values unless explicitly stated.
- Keep trend_judgement to one sentence.

JSON schema:

{
  "project_name": "string | null",
  "country": "string | null",
  "procurement_org": "string | null",
  "award_company": "string | null",
  "technologies": ["string"],
  "amount": "string | null",
  "currency": "string | null",
  "published_at": "ISO-8601 string | null",
  "source_url": "string | null",
  "trend_judgement": "string | null"
}
