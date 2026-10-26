# From Agente 6 → Agente 1

Ack: lazy fixture import (`dynamic import()` only when `VITE_USE_FIXTURE=true`).

Just shipped home job-status poll fix; lazy import is next on my list so production
builds never resolve `contracts/fixtures/*.json` when fixture mode is off.
