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

### `parlay-tracker/`
App web de un solo archivo (`index.html`) para registrar apuestas tipo parlay
y ver cómo va tu dinero con gráficas. Calcula automáticamente momios
combinados, pago potencial, probabilidad implícita, ganancia/pérdida, ROI y
win rate; incluye gráfica de evolución de la banca, dona de resultados y
barras por boleto. Guarda los datos en el navegador (localStorage); no maneja
dinero real, solo registra tus apuestas.

Para usarla: abre `parlay-tracker/index.html` en el navegador (doble clic).

### `ai-trader/`
Bot de trading **real** en Python conectado a Alpaca (bróker regulado con API).
Tu dinero vive en tu cuenta de Alpaca; el código solo manda órdenes ahí con tus
llaves. Incluye una estrategia fundamental (puntúa un universo con datos de
Yahoo Finance y elige las mejores) y comandos para ver cuenta/posiciones, comprar,
vender, invertir y rebalancear. Arranca en *paper* (práctica); para dinero real
cambias `ALPACA_PAPER=false`. No es asesoría financiera.

```bash
cd ai-trader && pip install -r requirements.txt && cp .env.example .env
python trader.py strategy        # prueba la estrategia (no necesita llaves)
```

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
