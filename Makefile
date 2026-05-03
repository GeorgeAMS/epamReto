start:
	docker compose up -d

stop:
	docker compose down

api:
	uv run uvicorn api.main:app --reload --port 8000

web:
	cd apps/web && npm run dev

demo:
	@echo "Frontend: http://localhost:3000"
	@echo "API: http://localhost:8000/docs"
	@echo "Langfuse: http://localhost:3001"
