# API Summary

All protected endpoints require:

```text
Authorization: Bearer <access_token>
```

## Auth

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/auth/register` | Create account and send verification OTP |
| POST | `/api/auth/verify-email` | Verify registration OTP and issue tokens |
| POST | `/api/auth/login` | Login and issue tokens |
| POST | `/api/auth/refresh` | Rotate refresh token and issue new token pair |
| POST | `/api/auth/logout` | Revoke refresh token |
| POST | `/api/auth/forgot-password` | Send reset OTP if account exists |
| POST | `/api/auth/reset-password` | Reset password with OTP |
| POST | `/api/auth/change-password` | Change password for authenticated user |
| GET | `/api/auth/me` | Get current user |

## CV

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/cvs/upload` | Upload PDF CV |
| GET | `/api/cvs` | List current user's CVs |
| DELETE | `/api/cvs/delete/<cv_id>` | Delete CV and related match reports |
| GET | `/api/cvs/file/<cv_id>` | Get temporary file URL |

## JD

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/jds/upload` | Upload JD PDF/TXT or manual text |
| GET | `/api/jds` | List current user's JDs |
| DELETE | `/api/jds/delete/<jd_id>` | Delete JD and related match reports |
| GET | `/api/jds/file/<jd_id>` | Get temporary file URL |

## Match Reports

| Method | Path | Description |
| --- | --- | --- |
| POST | `/api/matches` | Create CV-JD match report |
| GET | `/api/matches?limit=10&offset=0` | Paginated match history |
| GET | `/api/matches/<match_id>` | Match report detail |
| DELETE | `/api/matches/<match_id>` | Delete one report from history |
| GET | `/api/matches/download/<match_id>` | Download Word report |

## Pagination Response

`GET /api/matches` returns:

```json
{
  "matches": [],
  "pagination": {
    "limit": 10,
    "offset": 0,
    "total": 0,
    "has_next": false,
    "has_prev": false
  }
}
```
