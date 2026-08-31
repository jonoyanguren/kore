.PHONY: start back front stop help account-on account-off

APP ?= kore

# Consola local: API (8000) + Vite (5173). Ctrl+C para ambos.
start:
	@echo "API  http://127.0.0.1:8000"
	@echo "UI   http://127.0.0.1:5173  (proxy /api → back)"
	@trap 'kill 0' INT TERM EXIT; \
		uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 & \
		npm --prefix web run dev & \
		wait

back:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

front:
	npm --prefix web run dev

# Mata lo que esté en 8000 / 5173 (por si quedó huérfano).
stop:
	-@lsof -tiTCP:8000 -sTCP:LISTEN | xargs kill 2>/dev/null || true
	-@lsof -tiTCP:5173 -sTCP:LISTEN | xargs kill 2>/dev/null || true
	@echo "stopped (8000 / 5173)"

# Cortar / reactivar una cuenta (columna `allowed` en /data/accounts.db).
#   make account-off EMAIL=ana@x.com
#   make account-on EMAIL=ana@x.com
account-off:
	@test -n "$(EMAIL)" || { echo "uso: make account-off EMAIL=a@x.com" >&2; exit 1; }
	fly ssh console -a $(APP) -C "python -m app.accounts.flag off $(EMAIL)"

account-on:
	@test -n "$(EMAIL)" || { echo "uso: make account-on EMAIL=a@x.com" >&2; exit 1; }
	fly ssh console -a $(APP) -C "python -m app.accounts.flag on $(EMAIL)"

help:
	@echo "make start           — API + Vite juntos"
	@echo "make back            — solo FastAPI :8000"
	@echo "make front           — solo Vite :5173"
	@echo "make stop            — mata puertos 8000/5173"
	@echo "make account-off EMAIL=a@x.com         — corta esa cuenta (Fly)"
	@echo "make account-on EMAIL=a@x.com          — la reactiva"
