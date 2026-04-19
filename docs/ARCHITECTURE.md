# Architecture

## Overview

CV Reviewer has two main applications:

- Flask API backend for authentication, document processing, matching, reporting, and storage integration.
- React/Vite frontend for user workflows and report visualization.

```text
Browser
  |
  | React + Axios
  v
Flask API
  |
  |-- Auth services: password hashing, OTP, JWT, refresh-token rotation
  |-- Document services: PDF/TXT extraction, Supabase Storage upload
  |-- Matching services: skills, keyword, semantic, experience, structure
  |-- Report services: JSON report and DOCX export
  |
  v
Database + Redis + Supabase Storage
```

## Main Data Flow

1. User registers and verifies email with OTP.
2. User uploads CV PDF and JD PDF/TXT or manually enters JD text.
3. Backend extracts text and stores document metadata plus extracted text.
4. User creates a match from one CV and one JD.
5. Backend parses CV sections, runs rule checks, runs JD matching, builds report JSON, and stores match history.
6. Frontend displays the report and can download a DOCX version.
7. User can browse paginated report history or delete a report.

## Matching Layers

- Skill coverage: required and preferred skills detected in JD compared with CV.
- Keyword match: technical keywords and skills only, excluding salary, benefits, and administrative lines.
- Semantic match: semantic similarity between JD responsibilities and CV experience/project evidence.
- Experience alignment: seniority, years, and responsibility fit.
- Structure and writing quality: sections, contact info, measurable impact, weak phrases, action verbs.

## Security Boundaries

- Supabase service role key is backend-only and must never be exposed to the frontend.
- JWT access tokens protect API routes.
- Refresh tokens are stored hashed in the database and rotated on refresh.
- Redis stores OTPs and rate-limit counters with TTLs.
- CV/JD files should use private storage plus signed URLs or backend proxy download.

## Current Improvement Notes

- Use Alembic migrations before production deployment.
- Add CI for backend tests and frontend build.
- Add route-level request schemas to reduce manual validation.
- Keep `.env` private and rotate any previously exposed credentials.
