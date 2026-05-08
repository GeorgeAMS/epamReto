# Deployment - Pokedex Arcana

## Arranque para demo

### Terminal 1: Backend
```powershell
cd C:\Users\jorge\pokeArca
.\start_backend_clean.ps1
```
Esperar: `Application startup complete`

### Terminal 2: Frontend
```powershell
cd C:\Users\jorge\pokeArca\apps\pokedex-arcana-frontend
Copy-Item .env.example .env -ErrorAction SilentlyContinue
npm run dev
```
Esperar: mensaje `ready` de Vite (puerto en consola, p. ej. 5173 o 8080).

### Terminal 3: Verificacion
```powershell
cd C:\Users\jorge\pokeArca
.\test_backend.ps1
```
Esperar: todos los tests en `OK`.

## Checklist pre-demo

- [ ] Backend arranca sin errores
- [ ] Health check OK
- [ ] Query `hola` conversacional
- [ ] Query `pikachu` no robotica
- [ ] Team building funciona
- [ ] Frontend carga (URL que indique Vite)
- [ ] Frontend usa API `:18001`

## Troubleshooting

### Backend no arranca
```powershell
cd C:\Users\jorge\pokeArca\apps\api
python -c "import sys; print('\n'.join(sys.path))"
```

### Tests fallan
```powershell
cd C:\Users\jorge\pokeArca
.\start_backend_clean.ps1
.\test_backend.ps1
```

### Frontend no conecta
```powershell
cd C:\Users\jorge\pokeArca
Get-Content .\apps\pokedex-arcana-frontend\.env
```
Debe decir: `VITE_API_URL=http://127.0.0.1:18001` (o tu URL pública del API).

---

## API con Docker (misma imagen que nube)

Desde la raíz del repo (con `cp .env.example .env` y claves rellenadas):

```bash
docker compose build api
docker compose up -d qdrant ollama langfuse-db langfuse
docker compose up -d api
```

La API queda en `http://127.0.0.1:18001` (mapeo `18001:8000`). DuckDB y caché PokéAPI van en el volumen `api_data`; PDFs en `api_reports`.

Imagen suelta:

```bash
docker build -t pokedex-api .
docker run --rm -p 18001:8000 --env-file .env pokedex-api
```

(Ajusta `QDRANT_URL` si Qdrant no está en la misma red Docker.)

## API en la nube (Fly.io)

Hay un `fly.toml` en la raíz. Qdrant y Ollama **no** pueden ser `localhost` dentro del contenedor: usa [Qdrant Cloud](https://cloud.qdrant.io/) (u otro) y embeddings con `EMBEDDING_PROVIDER=gemini` o URL pública de Ollama.

```bash
fly auth login
fly launch --no-deploy   # o fly apps create … y fly deploy
fly secrets set GROQ_API_KEY=… GEMINI_API_KEY=…
fly secrets set QDRANT_URL=https://… QDRANT_API_KEY=…
fly secrets set ENV=prod API_CORS_ORIGINS=https://pokedex-arcana-frontend.vercel.app
fly deploy
```

En Windows, si instalaste el CLI con el script de Fly, el binario puede estar en `%USERPROFILE%\.fly\bin\flyctl.exe` (usa `flyctl` o añade esa carpeta al `PATH`).

URL pública tipo `https://pokedex-arcana-api.fly.dev` → pégala en Vercel como `VITE_API_URL` (Project Settings → Environment Variables → Production).

## Front (Vercel) + API

1. Despliega la API (Fly, Railway, Render, etc.) y copia su URL HTTPS.
2. En Vercel (proyecto del front): `VITE_API_URL=<esa URL>`.
3. En el host de la API: `API_CORS_ORIGINS` debe incluir `https://tu-proyecto.vercel.app` (y previews si las usas).
