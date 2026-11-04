PY ?= .venv/bin/python
COMPOSE = docker compose -f infrastructure/compose.yaml --env-file .env.local
COMPOSE_WAIT_TIMEOUT ?= 600
PROFILE ?=
PROFILE_FLAG = $(if $(PROFILE),--profile $(PROFILE))
QDRANT_URL ?= http://127.0.0.1:6333
QDRANT_COLLECTION ?= bank_docs
BACKUP_DIR ?= data/backups/qdrant

.PHONY: setup check test lint validate up smoke down logs ui n8n-up n8n-import backup restore

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
	$(COMPOSE) $(PROFILE_FLAG) up -d --build --wait --wait-timeout $(COMPOSE_WAIT_TIMEOUT)

smoke:
	curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8000/health
	curl --fail --silent --show-error --max-time 10 http://127.0.0.1:6333/readyz
	$(COMPOSE) exec -T redis redis-cli -e ping

down:
	$(COMPOSE) $(PROFILE_FLAG) down

# Streamlit demo UI (T-042) on 127.0.0.1:8501; reads UI_API_URL and UI_KEY_* from .env.local.
ui:
	set -a; [ ! -f .env.local ] || . ./.env.local; set +a; \
	$(PY) -m streamlit run ui/app.py --server.address 127.0.0.1 --server.headless true

logs:
	$(COMPOSE) $(PROFILE_FLAG) logs -f --tail=100

backup restore:
	$(PY) scripts/qdrant_backup.py $@ --url "$(QDRANT_URL)" --collection "$(QDRANT_COLLECTION)" --backup-dir "$(BACKUP_DIR)"

n8n-up:
	$(COMPOSE) --profile automation up -d --wait --wait-timeout $(COMPOSE_WAIT_TIMEOUT) n8n mailpit

# The stable workflow ID makes re-import update the same, unpublished workflow.
n8n-import:
	$(COMPOSE) --profile automation run --rm --no-deps n8n import:workflow --input=/workflows/error-handler.json
	$(COMPOSE) --profile automation run --rm --no-deps n8n import:workflow --input=/workflows/intake-to-reply.json
