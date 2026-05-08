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

## API en la nube gratis (Render recomendado)

Hay un `render.yaml` en la raiz para dejar el backend listo.

1. Sube este repo a GitHub.
2. En Render: **New +** -> **Blueprint** -> selecciona tu repo.
3. Render detecta `render.yaml` y crea `pokedex-arcana-api` en plan free.
4. En variables (o en el propio Blueprint), define:
   - `GROQ_API_KEY`
   - `GEMINI_API_KEY` (si `EMBEDDING_PROVIDER=gemini`)
   - `QDRANT_URL` y `QDRANT_API_KEY` (Qdrant Cloud)
   - `AUTH_USER`, `AUTH_PASSWORD`, `AUTH_TOKEN_SECRET`
   - `API_CORS_ORIGINS=https://<tu-front>.vercel.app`
5. Espera deploy y valida `https://<tu-api>.onrender.com/health`.

Notas:
- Free tier puede "dormir" la API sin trafico (cold start).
- No uses `localhost` para Qdrant en nube; usa endpoint publico.

## API en la nube (Fly.io alternativa)

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

Hay un `apps/pokedex-arcana-frontend/vercel.json` listo para SPA routing.

1. En Vercel: **Add New Project** y selecciona este repo.
2. Define:
   - **Root Directory**: `apps/pokedex-arcana-frontend`
   - **Build Command**: `npm install && npm run build`
   - **Output Directory**: `dist`
3. Agrega variable de entorno:
   - `VITE_API_URL=https://<tu-api>.onrender.com`
4. Deploy.
5. En el backend, confirma:
   - `API_CORS_ORIGINS=https://<tu-proyecto>.vercel.app`

## Checklist de salida (internet, gratis y funcional)

- [ ] `GET /health` responde `status=ok` en URL publica.
- [ ] Login funciona en front contra backend publico.
- [ ] Chat (`/chat` y `/chat/stream`) responde sin CORS errors.
- [ ] `VITE_API_URL` en Vercel apunta al backend publico.
- [ ] No hay secretos en git (solo en variables de entorno).
