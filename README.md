# CV Reviewer

CV Reviewer is a graduation-project style web application for comparing a candidate CV against a job description. The system extracts CV/JD text, evaluates fit across multiple scoring layers, explains gaps, and generates a downloadable Word report.

## Core Features

- Email/password authentication with OTP email verification.
- JWT access tokens and refresh-token rotation.
- CV and JD upload, including PDF/TXT extraction.
- CV-JD matching with skill, keyword, semantic, experience, and structure checks.
- Explainable match report with missing skills, weak bullets, missing metrics, and rewrite suggestions.
- Match history with pagination, report detail view, Word export, and report deletion.
- React dashboard with separate sections for CVs, JDs, matching, and report history.
- Vietnamese/English UI support.

## Tech Stack

- Backend: Flask, SQLAlchemy, PyJWT, bcrypt, Redis, pdfplumber, scikit-learn, sentence-transformers, python-docx.
- Frontend: React, Vite, React Router, Axios, Tailwind CSS.
- Storage: Supabase Storage.
- Database: PostgreSQL in production, SQLite fallback for local development.

## Project Structure

```text
.
├── app.py
├── src/
│   ├── api/                 # Flask routes
│   ├── core/                # JWT, auth dependencies, rate limiting
│   ├── data/                # Rules and skill taxonomy
│   ├── db/                  # SQLAlchemy models/session
│   └── services/            # Matching, reports, storage, parsing, auth
├── frontend/
│   └── src/                 # React application
├── docs/                    # Graduation-project documentation
├── test_matching_engine.py
├── requirements.txt
└── .env.example
```

## Setup

1. Create a local environment file.

```powershell
Copy-Item .env.example .env
```

2. Fill in `.env` values. For local-only development, `DATABASE_URL=sqlite:///cv_review.db` is enough. OTP and login protection require Redis.

3. Install backend dependencies.

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
```

4. Install frontend dependencies.

```powershell
cd frontend
npm install
```

5. Run backend.

```powershell
cd D:\cv-review
.\.venv\Scripts\activate
python app.py
```

6. Run frontend.

```powershell
cd D:\cv-review\frontend
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies `/api` to Flask on `http://localhost:5000`.

## Verification

Backend matching smoke test:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe test_matching_engine.py
```

Frontend production build:

```powershell
cd frontend
npm.cmd run build
```

## Security Notes

This repository must not contain real credentials. Use `.env` locally and rotate any credential that has ever been committed or shared.

Required external actions after any accidental secret exposure:

- Rotate Supabase service role and anon keys.
- Change the database password or regenerate the database connection string.
- Revoke Gmail app passwords or SMTP credentials.
- Replace `JWT_SECRET_KEY`.
- Revoke any third-party API keys that were committed.
- Consider rewriting git history if the repository is public or has been shared.

## Documentation

See:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/API.md](docs/API.md)
- [docs/GRADUATION_CHECKLIST.md](docs/GRADUATION_CHECKLIST.md)
