# To Agente 7 — Makefile e2e → isolated stack

Root `Makefile` `e2e` target now runs `cd e2e && npm install && npm test`
(isolated `takeoff_e2e` / `:5174`). Comment notes never use default takeoff DB.
