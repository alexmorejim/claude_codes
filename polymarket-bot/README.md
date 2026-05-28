# polymarket-bot

Apuesta en [Polymarket](https://polymarket.com) con **dinero real** y un
**auto-bet** opcional. Polymarket es no-custodial: tu dinero (USDC en Polygon)
vive en **tu** wallet; el bot solo firma órdenes con tu llave. Leer mercados,
precios y posiciones no necesita llave; apostar sí.

> **No es asesoría financiera. Puedes perder todo tu dinero. Ninguna estrategia
> automática garantiza ganancias** — los bots de "parlay que multiplica" que
> circulan en redes son estafas. Esto se conecta a la Polymarket real, tú
> controlas todo, y no promete rendimientos.

## Seguridad (léelo)

- Usa una **wallet dedicada** con **poco saldo**, no tu wallet principal.
- Tu llave privada vive **solo en `.env`**, que está en `.gitignore` y nunca se
  sube. Quien tenga esa llave controla todos los fondos de la wallet.
- Empieza con montos chicos (`AUTOBET_STAKE_USD=1`) y `autobet` en simulación.

## Instalación

```bash
cd polymarket-bot
pip install -r requirements.txt
cp .env.example .env        # y rellena (al menos POLY_PRIVATE_KEY)
```

## Preparar la wallet (una vez)

1. Ten USDC (de Polygon) en tu wallet. Si depositaste por la web de Polymarket,
   lee la nota de `POLY_FUNDER` / `POLY_SIGNATURE_TYPE` en `.env.example`.
2. Aprueba el gasto de USDC (tx on-chain única):
   ```bash
   python bot.py setup
   python bot.py balance      # confirma saldo y allowance
   ```

## Uso

```bash
python bot.py markets "trump" --max 15   # busca mercados + precios (sin llave)
python bot.py price <token_id>           # mejor compra/venta
python bot.py positions                  # tus posiciones
python bot.py buy <token_id> --usd 5     # compra $5 de ese resultado (REAL)
python bot.py sell <token_id> --shares 10
```

## Auto-bet

Define la regla en `.env` (`AUTOBET_*`): lado (favorito/longshot/yes/no), banda
de precio, monto por apuesta, máximo de apuestas y presupuesto.

```bash
python bot.py autobet         # SIMULACIÓN: muestra qué apostaría (no gasta)
python bot.py autobet --live  # apuesta de verdad (pide CONFIRMAR)
```

### Que apueste solo (automático)

Programa el comando con `cron`. Ejemplo: cada día a las 9:00 con un tope diario:

```cron
0 9 * * *  cd ~/claude_codes/polymarket-bot && /usr/bin/python3 bot.py autobet --live --yes >> autobet.log 2>&1
```

El presupuesto por corrida (`AUTOBET_BUDGET_USD`) limita cuánto arriesga cada
vez. Empieza en simulación varios días antes de poner `--live`.
