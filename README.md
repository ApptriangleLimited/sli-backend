# SLI Backend

FastAPI backend for SLI with PostgreSQL, SQLAlchemy, JWT authentication, role-based access, and admin user management.

## Requirements

- Python 3.12+
- PostgreSQL
- pip

## Local Setup

```bash
cd /sli-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env` if needed:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/sli_db
JWT_SECRET_KEY=change_this_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS=7
REFRESH_TOKEN_EXPIRE_DAYS=30
```

Create PostgreSQL database:

```bash
createdb sli_db
```

If permission fails:

```bash
sudo -u postgres createdb sli_db
```

## Run Backend

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at:

```txt
http://localhost:8000
```

API docs:

```txt
http://localhost:8000/docs
```

Health check:

```bash
curl http://localhost:8000/health
```

## Startup Behavior

On startup, backend will:

- Create missing tables.
- Add safe missing columns when possible.
- Seed default roles: `agent`, `underwriter`, `admin`.
- Seed default admin if missing.

Default admin:

```txt
Email: admin@apptriangle.com
Password: admin@3$!12313__)(
Role: admin
```

## Login Test

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@apptriangle.com",
    "password": "admin@3$!12313__)(",
    "remember_me": true
  }'
```

Use access token:

```txt
Authorization: Bearer <access_token>
```

Admin protected route:

```bash
curl http://localhost:8000/api/admin/dashboard \
  -H "Authorization: Bearer <access_token>"
```

## Postman

Import these files into Postman:

- `postman_collection.json`
- `postman_environment.json`

Select `SLI Backend Local` environment, then run `Login Admin` first. It saves `access_token` and `refresh_token` automatically for protected APIs.

## Available APIs

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh-token`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/admin/dashboard`
- `POST /api/admin/users`
