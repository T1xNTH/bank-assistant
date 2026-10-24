PY ?= .venv/bin/python
COMPOSE = docker compose -f infrastructure/compose.yaml --env-file .env.local

.PHONY: setup check test lint validate up down logs

setup:
	python3 -m venv .venv && $(PY) -m pip install -q -r requirements-dev.txt

lint:
	$(PY) -m ruff check .

test:
	$(PY) -m pytest -q

validate:
	python3 scripts/validate-framework.py

check: lint test validate

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100
