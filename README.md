# claude_codes

Colección de proyectos de código. Cada subcarpeta es un proyecto
independiente y autocontenido.

## Proyectos

### `analisis-acciones-nasdaq/`
Análisis fundamental de 5 acciones tecnológicas del NASDAQ 100 (NVDA, MSFT,
AAPL, GOOGL, META). Descarga datos reales de Yahoo Finance, las puntúa con un
modelo transparente de 7 factores (incluido el P/E ratio) y genera un reporte
en Word con una recomendación de compra.

```bash
cd analisis-acciones-nasdaq
pip install -r requirements.txt
python3 tech_analysis.py
```

Produce `data.json` (datos puntuados) y `Analisis_Tecnologicas.docx` (reporte).

### `polymarket-bot/`
Bot para apostar en Polymarket (dinero real, on-chain en Polygon) con un
**auto-bet** configurable. No-custodial: tu USDC vive en tu wallet, el bot solo
firma órdenes con tu llave (que vive solo en `.env`, nunca se sube). Lee
mercados/precios/posiciones sin llave; el auto-bet arranca en simulación y pasa
a real con `--live`. No es asesoría financiera; ninguna estrategia garantiza ganar.

```bash
cd polymarket-bot && pip install -r requirements.txt && cp .env.example .env
python bot.py markets "trump"    # explora mercados (sin llave)
python bot.py autobet            # simula la estrategia
```
