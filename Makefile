SHELL := /bin/sh

.PHONY: help frontend-install frontend-dev frontend-build frontend-lint backend-install backend-dev backend-migrate backend-seed backend-test backend-celery test build docker-up docker-down

help:
	@echo "ShopMind AI commands:"
	@echo "  make frontend-install  Install frontend dependencies"
	@echo "  make frontend-dev      Start Next.js dev server"
	@echo "  make frontend-build    Build frontend"
	@echo "  make frontend-lint     Lint frontend"
	@echo "  make backend-install   Install backend dependencies"
	@echo "  make backend-dev       Start FastAPI dev server"
	@echo "  make backend-migrate   Run Alembic migrations"
	@echo "  make backend-seed      Seed demo data"
	@echo "  make backend-test      Run backend tests"
	@echo "  make backend-celery    Start Celery worker"
	@echo "  make test              Run backend tests and frontend lint"
	@echo "  make build             Build frontend"
	@echo "  make docker-up         Start local full stack"
	@echo "  make docker-down       Stop local full stack"

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

backend-install:
	cd backend && pip install -r requirements.txt

backend-dev:
	cd backend && uvicorn main:app --reload

backend-migrate:
	cd backend && alembic upgrade head

backend-seed:
	cd backend && python scripts/seed_demo_data.py

backend-test:
	cd backend && python -m pytest

backend-celery:
	cd backend && celery -A app.tasks.celery_app worker --loglevel=info

test: backend-test frontend-lint

build: frontend-build

docker-up:
	docker compose up --build

docker-down:
	docker compose down
