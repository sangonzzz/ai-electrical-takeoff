# Rules for every agent (read before doing anything)

You are one of 8 agents building `ai-electrical-takeoff` in parallel, in the SAME local folder and the SAME git
branch (`main`). Santiago (GitHub `sangonzzz`) coordinates. The technical source of truth is `docs/SPEC.md`.

## Team

| Agent     | Area                                   | Owns (only you edit these paths)                                                        |
|-----------|----------------------------------------|-----------------------------------------------------------------------------------------|
| Agente 1  | Lead, architecture, integration        | root files, `AGENTS.md`, `docs/SPEC.md`, `docs/architecture.md`, `coordination/DECISIONS.md`, `contracts/`, `engine/takeoff_engine/{models,types,takeoff,config,cli,pdf_context}.py`, `engine/pyproject.toml`, `backend/pyproject.toml`, `web/src/types/contracts.ts`, `docker-compose.yml`, `Makefile`, `.github/` |
| Agente 2  | Symbol engine                          | `engine/takeoff_engine/{viewport,legend,symbols,classify,pipeline}.py`, `engine/tests/symbols/` |
| Agente 3  | Rooms                                  | `engine/takeoff_engine/rooms.py`, `engine/tests/rooms/`                                  |
| Agente 4  | AI with Claude                         | `engine/takeoff_engine/llm/`, `engine/prompts/`, `engine/tests/llm/`                     |
| Agente 5  | Backend API, jobs, database            | `backend/` (except `backend/pyproject.toml`: request changes to Agente 1)               |
| Agente 6  | Frontend                               | `web/`                                                                                  |
| Agente 7  | Evaluation, quality, CI checks         | `eval/`, `engine/takeoff_engine/overlay.py`, `engine/tests/eval/`, eval part of `cli.py` via request to Agente 1 |
| Agente 8  | Bill of materials                      | `engine/takeoff_engine/{wires,boxes,bom,pricing}.py`, `data/price_list.yaml`, `data/assumptions.yaml`, `engine/tests/bom/` |

Everyone also owns `coordination/status/agente-N.md` (your own number) and `docs/modules/<your-module>.md`.

## Hard rules

1. **Only edit paths you own.** Need a change somewhere else? Send a message (below). Never "quickly fix" another
   agent's file.
2. **Never run destructive git commands:** no `git reset`, `git checkout -- .`, `git restore .`, `git clean`,
   `git stash`, `git rebase`, `git push --force`. Other agents have uncommitted work in this same folder.
3. **Commit only your own paths:** `git add <your paths> && git commit -m "[A<N>] <type>(<scope>): <message>"`.
   If `.git/index.lock` exists, wait 5 seconds and retry. Small, frequent commits.
4. **Only Agente 1 pushes to GitHub.** Others commit locally.
5. **Git identity:** all commits are authored by Santiago's account `sangonzzz`. Do not change git config, do not use
   or create any other account, do not add co-authors.
6. **Secrets:** never commit `.env`, keys, tokens or credentials. Use `.env.example` with empty values. If a key is
   missing or expired, write it under "Needs from Santiago" in your status file and tell Santiago in chat.
7. **Contracts are frozen** (`engine/takeoff_engine/models.py`, `contracts/`). Changes go through Agente 1.
8. **Dependencies:** Python dependencies live in `engine/pyproject.toml` and `backend/pyproject.toml`
   (owned by Agente 1). Ask Agente 1 for new ones. Agente 6 manages `web/package.json` alone.
9. **Tests:** every non-trivial function gets a pytest (or Vitest) test. Tests never call the network; LLM calls use
   recorded fixtures or fakes.
10. **No silent guessing.** If the spec is ambiguous, pick the most reasonable option, record it in your status file
    under "Decisions", and message Agente 1 so it lands in `coordination/DECISIONS.md`.
11. **Explainability:** Santiago must defend every line in a technical interview. Prefer simple, readable code over
    clever code. Docstrings explain WHY. Write `docs/modules/<module>.md` (English): what it does, algorithm,
    parameters and thresholds, known limits.
12. **Visual debugging:** engine agents must render debug PNGs to `out/debug/` (gitignored) and look at them before
    claiming something works.
13. **Pipeline version:** `PIPELINE_VERSION` / `__version__` live only in
    `engine/takeoff_engine/__init__.py` (semver). CLI, `analyze_sheet` (`SheetResult.pipeline_version`),
    and the backend idempotency key all use that string. **Any engine behavior change must bump at least
    the patch** (Agente 1 applies the bump, or you ask Agente 1) so
    `(file_hash, page_index, pipeline_version)` never serves a stale run. Do not define a second version
    constant in `pipeline.py` or elsewhere.
14. **Engine freeze (from v0.4.0):** do **not** change engine detection/rooms/LLM/BOM/overlay behavior
    unless Santiago approves. File a message to Agente 1 with the proposal; Agente 1 bumps
    `PIPELINE_VERSION` only after approval. Docs, tests that lock current behavior, backend, and
    frontend may continue.

## Communication protocol (agents do not see each other's chats; files are the channel)

- **Status:** keep `coordination/status/agente-N.md` updated after each milestone with these sections:
  `Estado` (one line), `Hecho`, `Cómo probarlo` (exact commands), `Siguiente`, `Bloqueos`, `Decisions`,
  `Needs from Santiago`, and `Explicación para Santiago` (in Spanish, plain words, 5 to 10 lines: what you built,
  how it works, why this approach).
- **Messages:** to talk to another agent, create a NEW file
  `coordination/messages/<YYYYMMDD-HHMM>__from-agente-X__to-agente-Y__<topic>.md`
  (to everyone: `to-all`). Never edit an existing message file. Reply with a new file.
- **Check your inbox** at the start of every work session, before each commit, and whenever Santiago tells you
  "revisa tus mensajes": list `coordination/messages/` for files with `to-agente-N` or `to-all` you have not answered.
- When you finish a milestone that unblocks someone, send them a message saying what is ready and how to use it.

## Definition of done (for any task)

Code + tests passing + debug evidence (when visual) + status file updated + module doc updated + committed.
