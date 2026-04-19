# Graduation Checklist

## Completed in Code

- End-to-end CV/JD matching workflow.
- Authentication with OTP verification and refresh-token rotation.
- CV/JD upload and extracted text storage.
- Multi-layer matching engine.
- Explainable JSON report and DOCX export.
- Match history with pagination and delete support.
- Sidebar dashboard with separate sections.
- Basic project documentation and environment template.

## Must Do Outside Code

- Rotate any credential that was ever committed or shared:
  - Supabase service role key.
  - Supabase anon key if desired.
  - Database password/connection string.
  - SMTP app password.
  - JWT secret.
  - Any third-party API key.
- Confirm Supabase buckets are private if real CV data is used.
- If the repository is public or has been shared, remove leaked secrets from git history with BFG or `git filter-repo`.

## Recommended Before Defense

- Add screenshots or a short demo video.
- Prepare a seeded demo account and sample CV/JD files.
- Add an ERD diagram for users, documents, refresh tokens, and match history.
- Add sequence diagrams for registration, upload, and matching.
- Add pytest route tests and GitHub Actions CI.
- Add Alembic migrations for database schema control.

## Suggested Defense Talking Points

- Why multiple scoring layers are better than one cosine similarity score.
- How evidence-based feedback helps users improve CV quality.
- How JWT, refresh-token rotation, hashed tokens, OTP TTL, and rate limiting improve security.
- Current limitations: PDF extraction quality, model availability, private storage policy, and lack of large benchmark dataset.
