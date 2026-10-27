PY ?= .venv/bin/python
COMPOSE = docker compose -f infrastructure/compose.yaml --env-file .env.local
COMPOSE_WAIT_TIMEOUT ?= 120

.PHONY: setup check test lint validate up smoke down logs

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
	$(COMPOSE) up -d --build --wait --wait-timeout $(COMPOSE_WAIT_TIMEOUT)

smoke:
	curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/health
	curl --fail --silent --show-error --max-time 10 http://127.0.0.1:6333/readyz
	$(COMPOSE) exec -T redis redis-cli -e ping

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100
