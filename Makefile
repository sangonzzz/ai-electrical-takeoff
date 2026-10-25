.PHONY: setup up down logs test lint schema analyze eval demo

setup:
	uv sync --all-packages --group dev
	@if [ -f web/package.json ]; then cd web && corepack enable && pnpm install; fi

up:
	docker compose up -d --build

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
	uv run takeoff analyze data/plans/escondido_plans.pdf --page 0 --out out/sheet_result.json --debug

eval:
	uv run takeoff eval --out eval/reports

demo:
	@echo "Start stack with: make up"
	@echo "Then open http://localhost:5173 and load data/plans/escondido_plans.pdf"
