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
cd C:\Users\jorge\pokeArca\apps\web
npm run dev
```
Esperar: `ready - started server on 0.0.0.0:3000`

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
- [ ] Frontend carga en `:3000`
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
Get-Content .\apps\web\.env.local
```
Debe decir: `NEXT_PUBLIC_API_URL=http://127.0.0.1:18001`
