# Job CRM — AI-Powered Job Application Manager

## Overview
Single-user CRM for job searching on BOSS Zhipin. Scores jobs against your CV using Claude,
drafts personalized messages, tracks applications, and requires human approval before anything is sent.

## Stack
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, Python 3.12, SQLModel, asyncpg
- **Queue**: Redis + Celery
- **DB**: PostgreSQL 16
- **AI**: Anthropic Claude API
- **Automation**: Playwright (Phase 4+)

## Running Locally

```bash
cp .env.example .env
# Edit .env with real values
docker-compose up
```

- Frontend: http://localhost:3000
- Backend API docs: http://localhost:8000/api/docs
- Default login: admin@example.com / changeme (set in .env)

## Running Migrations

```bash
docker-compose exec backend alembic upgrade head
```

## Running Tests

```bash
docker-compose exec backend pytest
```

Or locally (requires aiosqlite):
```bash
cd backend && pip install aiosqlite pytest-asyncio httpx && pytest
```

## Key Environment Variables

| Variable | Purpose |
|---|---|
| ADMIN_EMAIL / ADMIN_PASSWORD | Single-user login credentials |
| JWT_SECRET_KEY | Must be changed in production |
| ANTHROPIC_API_KEY | Claude API key (Phase 2+) |
| MAX_APPLICATIONS_PER_DAY | Safety rate limit (default 10) |

## Development Phases

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Done | Foundation: auth, profiles, jobs CRUD, Docker |
| 2 | ✅ Done | Claude scoring, AI audit log, application drafts, cost tracking |
| 3 | Planned | Approval workflow + Telegram notifications |
| 4 | Planned | Playwright job collection from BOSS Zhipin |
| 5 | Planned | Message sending + conversation tracking |
| 6 | Planned | Polish + production hardening |

## Safety Invariants (never remove)
- All Claude calls logged to `ai_audit_log`
- No messages sent without approval queue entry
- Browser automation hard-limited to 10 sends/day
- No CAPTCHA solving — pause and notify user if encountered
