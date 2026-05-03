# Setup rápido

```bash
bun install         # o: npm install / pnpm install
cp .env.example .env
# edita VITE_API_URL si tu FastAPI corre en otro host
bun dev             # http://localhost:8080 (o el que use Vite)
```

Backend esperado en `VITE_API_URL` (default `http://127.0.0.1:18001`).
