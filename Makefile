.PHONY: setup up down logs test lint schema analyze eval demo e2e

setup:
	uv sync --all-packages --group dev
	@if [ -f web/package.json ]; then cd web && corepack enable && pnpm install; fi

up:
	docker compose up -d --build
	@docker compose ps

down:
	docker compose down

logs:
	docker compose logs -f

test:
	uv run pytest

lint:
	uv run ruff check engine backend

schema:
	uv run takeoff schema
	@if command -v npx >/dev/null 2>&1; then \
		npx --yes json-schema-to-typescript contracts/schema.json -o web/src/types/contracts.ts; \
	fi

analyze:
	uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/sheet_result.json --debug

eval:
	uv run takeoff eval --out eval/reports

demo:
	@echo "Ensure stack is up: make up"
	uv run python backend/scripts/demo_upload.py
	@echo "Open http://localhost:5173"

# Playwright quality pass against the running docker stack (Agente 7).
# Requires: make up (api + web + worker healthy on :8000 / :5173).
e2e:
	cd e2e && npm install && npx playwright install chromium && npx playwright test
