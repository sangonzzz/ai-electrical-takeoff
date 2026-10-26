# E2E (Agente 7)

Playwright suite against the docker stack at `http://localhost:5173`.

```bash
make up          # api + web + worker
make e2e         # install browsers + run tests
```

Step pass/fail is written to `e2e/results/steps.md` (and `steps.json`).
Screenshots/traces land in `e2e/results/artifacts/` on failure.
