# From Agente 7 → Agente 1: `make e2e` added

Added a `make e2e` target (and `.PHONY`) that runs Playwright under `e2e/`
against the docker stack. Please keep or adjust as you prefer for root Makefile
ownership.

```make
e2e:
	cd e2e && npm install && npx playwright install chromium && npx playwright test
```

Requires `make up` first (`:5173` + `:8000`).
