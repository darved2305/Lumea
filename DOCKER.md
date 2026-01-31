# Docker Setup

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start everything
docker compose up

# 3. Access the app
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
# Database: localhost:5432
```

## Ports

| Service  | Port | Description            |
|----------|------|------------------------|
| Frontend | 5173 | Vite React dev server  |
| Backend  | 8000 | FastAPI server         |
| Database | 5432 | PostgreSQL             |

## Development Workflow

**Hot reload is enabled** - edit files locally and containers pick up changes:

- Edit `frontend/src/*` → Vite reloads automatically
- Edit `backend/app/*` → Uvicorn reloads automatically

## Common Commands

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend

# Rebuild after changing dependencies
docker compose build
docker compose up

# Stop everything
docker compose down

# Stop and remove volumes (wipes database)
docker compose down -v

# Run database migrations
docker compose exec backend alembic upgrade head

# Access database shell
docker compose exec db psql -U ggw -d ggwdb
```

## First-Time Setup

The database is initialized automatically. If you need to run migrations:

```bash
docker compose exec backend alembic upgrade head
```

## Troubleshooting

**Frontend not updating?**
- Vite uses polling for Docker. If changes aren't detected, restart the frontend:
  ```bash
  docker compose restart frontend
  ```

**Backend import errors after adding packages?**
- Rebuild the image:
  ```bash
  docker compose build backend
  docker compose up
  ```

**Database connection errors?**
- Wait for the db healthcheck to pass
- Check logs: `docker compose logs db`
