.PHONY: start back front stop help

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

help:
	@echo "make start  — API + Vite juntos"
	@echo "make back   — solo FastAPI :8000"
	@echo "make front  — solo Vite :5173"
	@echo "make stop   — mata puertos 8000/5173"
