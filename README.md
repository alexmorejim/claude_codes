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
