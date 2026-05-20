.PHONY: help up down build migrate test logs shell-backend shell-db prod-up prod-down prod-build

help:
	@echo "Job CRM — Available commands:"
	@echo "  make up            Start dev environment"
	@echo "  make down          Stop dev environment"
	@echo "  make build         Rebuild dev images"
	@echo "  make migrate       Run Alembic migrations"
	@echo "  make test          Run backend test suite"
	@echo "  make logs          Tail all service logs"
	@echo "  make shell-backend Open shell in backend container"
	@echo "  make shell-db      Open psql in db container"
	@echo "  make prod-build    Build production images"
	@echo "  make prod-up       Start production environment"
	@echo "  make prod-down     Stop production environment"

up:
	docker-compose up

down:
	docker-compose down

build:
	docker-compose build

migrate:
	docker-compose exec backend alembic upgrade head

test:
	docker-compose exec backend pytest -v

logs:
	docker-compose logs -f

shell-backend:
	docker-compose exec backend bash

shell-db:
	docker-compose exec db psql -U jobcrm jobcrm

prod-build:
	docker-compose -f docker-compose.prod.yml build

prod-up:
	docker-compose -f docker-compose.prod.yml up -d

prod-down:
	docker-compose -f docker-compose.prod.yml down
