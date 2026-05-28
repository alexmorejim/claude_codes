# ai-trader

Bot de trading **real** conectado a [Alpaca](https://alpaca.markets), un bróker
regulado con API. Tu dinero vive en **tu** cuenta de Alpaca; este código solo
manda órdenes ahí con tus llaves. Trae una estrategia fundamental (puntúa un
universo de acciones con datos de Yahoo Finance y elige las mejores).

Arranca en **paper** (dinero de práctica). Para dinero real cambias una línea.

## Instalación

```bash
cd ai-trader
pip install -r requirements.txt
cp .env.example .env      # y rellena tus llaves
```

Consigue llaves gratis en https://alpaca.markets. El modo **paper** no requiere
fondear ni verificar nada: te dan API key/secret de práctica al instante.

## Uso

```bash
python trader.py account              # resumen de cuenta y poder de compra
python trader.py positions            # posiciones abiertas con P&L
python trader.py quote NVDA           # precio actual
python trader.py strategy             # rankea el universo y muestra el plan (no opera)
python trader.py invest --usd 1000    # reparte $1000 entre las mejores (órdenes notional)
python trader.py rebalance --usd 1000 # cierra lo que no es pick y reinvierte
python trader.py buy AAPL --usd 200   # compra manual de $200
python trader.py sell AAPL --qty 3    # vende 3 acciones
python trader.py close AAPL           # cierra toda la posición
```

`strategy` no necesita llaves (solo lee datos públicos), así que puedes probar
la estrategia antes de conectar nada.

## Pasar a dinero real

1. Abre y **fondea** tu cuenta en Alpaca, genera llaves **live**.
2. En `.env`: pon esas llaves y `ALPACA_PAPER=false`.
3. Las órdenes en real piden escribir `CONFIRMAR` una vez (sáltalo con `--yes`).

## Configuración

En `.env`:
- `TRADER_TOP_N` — cuántas acciones elegir (def. 4).
- `TRADER_UNIVERSE` — lista de tickers a evaluar (def. 7 grandes tech).

## Aviso

Esto **no es asesoría financiera**. El trading con dinero real puede hacerte
perder capital. La estrategia incluida es simple y educativa; pruébala en paper
y entiéndela antes de arriesgar dinero. Tus llaves viven solo en `.env` (que
está en `.gitignore` y nunca se sube).
