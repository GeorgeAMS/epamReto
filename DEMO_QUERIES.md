# Queries de Demostracion - Pokedex Arcana

## TOP 10 para Demo (5 minutos)

### 1) Saludo conversacional
Query: `hola`  
Esperado: Respuesta amigable, no fallback generico  
Tiempo: `<2s`

### 2) Stats conversacional
Query: `Que sabes de Pikachu?`  
Esperado: Texto natural, no formato robotico tipo "Stats base: HP 35..."  
Tiempo: `<5s`

### 3) Comparacion
Query: `Compara Charizard vs Blastoise`  
Esperado: Analisis comparativo de stats  
Tiempo: `<7s`

### 4) Calculo simple
Query: `Cuanto dano hace Thunderbolt de Pikachu a Gyarados?`  
Esperado: Rango de dano exacto con porcentaje de HP  
Tiempo: `<5s`

### 5) Calculo con modificadores
Query: `Abomasnow naturaleza Audaz usa Blizzard vs Jigglypuff con 0 EVs SpD`  
Esperado: Calculo Gen IX completo + verificacion dual  
Tiempo: `<8s`

### 6) Team building (espanol)
Query: `Recomienda 5 companeros para Dragapult en OU`  
Esperado: Lista de 5 Pokemon con roles, EVs, items  
Tiempo: `<20s`

### 7) Team building (ingles)
Query: `I need 5 teammates for Garchomp in OU`  
Esperado: Lista con analisis estrategico  
Tiempo: `<20s`

### 8) Lore
Query: `Cuentame la historia de Mewtwo`  
Esperado: Sintesis de Bulbapedia + Pokedex entries  
Tiempo: `<8s`

### 9) Efectividad de tipos
Query: `Que tipos son super efectivos contra Dragonite?`  
Esperado: Ice, Dragon, Fairy, Rock  
Tiempo: `<4s`

### 10) Multi-fuente
Query: `Hablame de Garchomp: stats, tier y lore`  
Esperado: Fusion de PokeAPI + Smogon + Bulbapedia  
Tiempo: `<12s`

## Queries de backup

- `En que tier esta Tyranitar?`
- `Quien es mas rapido, Garchomp o Salamence?`
- `Pikachu con Light Ball usa Thunderbolt vs Garchomp en rain`
- `Que Pokemon tipo Water son buenos en OU?`
- `Analisis de Landorus-Therian como pivot defensivo`
