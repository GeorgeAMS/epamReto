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
