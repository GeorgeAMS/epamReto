start:
	docker compose up -d

stop:
	docker compose down

api:
	cd apps/api && uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 18001

web:
	cd apps/pokedex-arcana-frontend && npm run dev

demo:
	@echo "Frontend: ver URL en consola de Vite (apps/pokedex-arcana-frontend)"
	@echo "API: http://127.0.0.1:18001/docs"
	@echo "Langfuse: http://localhost:3001"
