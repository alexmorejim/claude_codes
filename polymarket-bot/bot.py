# -*- coding: utf-8 -*-
"""polymarket-bot — apuesta en Polymarket (dinero real, on-chain) con auto-bet.

Polymarket es no-custodial: tu dinero (USDC en Polygon) vive en TU wallet, no
en este código. El bot firma órdenes con tu llave privada (que vive solo en
.env, nunca se sube). Lee mercados/precios/posiciones sin llave; para apostar sí
la necesita.

El auto-bet por defecto es DRY-RUN (simula): te muestra qué apostaría. Para
apostar de verdad agregas --live.

Comandos:
  python bot.py markets "iran" --max 15      busca mercados abiertos + precios
  python bot.py price <token_id>             mejor precio (compra/venta)
  python bot.py positions                    tus posiciones (necesita POLY_ADDRESS o llave)
  python bot.py balance                      USDC disponible (necesita llave)
  python bot.py setup                         aprueba USDC una vez (allowance, necesita llave)
  python bot.py buy <token_id> --usd 5        compra $5 de ese resultado (real)
  python bot.py sell <token_id> --shares 10   vende 10 shares (real)
  python bot.py autobet                       simula la estrategia (dry-run)
  python bot.py autobet --live                ejecuta la estrategia con dinero real

NO es asesoría financiera. Apostar con dinero real puede hacerte perder todo.
Ninguna estrategia automática garantiza ganancias.
"""
import os
import sys
import json
import argparse

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

# ----- config -----
PRIVATE_KEY = os.getenv("POLY_PRIVATE_KEY", "").strip()
ADDRESS = os.getenv("POLY_ADDRESS", "").strip()
FUNDER = os.getenv("POLY_FUNDER", "").strip() or None
SIG_TYPE = os.getenv("POLY_SIGNATURE_TYPE", "").strip()
SIG_TYPE = int(SIG_TYPE) if SIG_TYPE else None

HOST = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"
CHAIN = 137

# auto-bet rules (todo configurable por .env)
AB = {
    "query": os.getenv("AUTOBET_QUERY", "").strip().lower(),
    "side": os.getenv("AUTOBET_SIDE", "favorite").strip().lower(),  # favorite|longshot|yes|no
    "min_price": float(os.getenv("AUTOBET_MIN_PRICE", "0.80")),
    "max_price": float(os.getenv("AUTOBET_MAX_PRICE", "0.97")),
    "stake_usd": float(os.getenv("AUTOBET_STAKE_USD", "2")),
    "max_bets": int(os.getenv("AUTOBET_MAX_BETS", "3")),
    "budget_usd": float(os.getenv("AUTOBET_BUDGET_USD", "6")),
    "min_volume": float(os.getenv("AUTOBET_MIN_VOLUME", "20000")),
}

GREEN, RED, DIM, BOLD, YEL, END = "\033[92m", "\033[91m", "\033[2m", "\033[1m", "\033[93m", "\033[0m"


def money(v):
    return "$" + f"{float(v):,.2f}"


def jload(s, default):
    try:
        return json.loads(s) if isinstance(s, str) else (s or default)
    except Exception:
        return default


# ----- API pública (sin llave) -----
def fetch_markets(query="", limit=20):
    r = requests.get(f"{GAMMA}/markets", params={
        "closed": "false", "active": "true", "limit": max(limit * 4, 40),
        "order": "volume24hr", "ascending": "false"}, timeout=30)
    r.raise_for_status()
    out = []
    for m in r.json():
        q = (m.get("question") or "")
        if query and query not in q.lower():
            continue
        toks = jload(m.get("clobTokenIds"), [])
        outs = jload(m.get("outcomes"), [])
        prices = [float(p) for p in jload(m.get("outcomePrices"), [])]
        if len(toks) < 2 or len(prices) < 2:
            continue
        out.append({
            "question": q, "tokens": toks, "outcomes": outs, "prices": prices,
            "volume24hr": float(m.get("volume24hr") or 0),
            "liquidity": float(m.get("liquidity") or 0),
        })
        if len(out) >= limit:
            break
    return out


def public_price(token_id, side="buy"):
    r = requests.get(f"{HOST}/price", params={"token_id": token_id, "side": side}, timeout=20)
    r.raise_for_status()
    return float(r.json().get("price", 0))


def fetch_positions(address):
    r = requests.get(f"{DATA}/positions", params={"user": address, "sizeThreshold": "0.1"}, timeout=30)
    if r.status_code >= 400:
        return []
    return r.json()


# ----- cliente con llave (para operar) -----
def get_client(need_creds=True):
    if not PRIVATE_KEY:
        sys.exit(f"{RED}Falta POLY_PRIVATE_KEY en .env.{END} (Usa una wallet dedicada con poco saldo.)")
    from py_clob_client.client import ClobClient
    kw = {"chain_id": CHAIN, "key": PRIVATE_KEY}
    if SIG_TYPE is not None:
        kw["signature_type"] = SIG_TYPE
    if FUNDER:
        kw["funder"] = FUNDER
    client = ClobClient(HOST, **kw)
    if need_creds:
        client.set_api_creds(client.create_or_derive_api_creds())
    return client


def my_address():
    if ADDRESS:
        return ADDRESS
    if PRIVATE_KEY:
        return get_client(need_creds=False).get_address()
    sys.exit(f"{RED}Necesito POLY_ADDRESS o POLY_PRIVATE_KEY en .env.{END}")


# ----- comandos -----
def cmd_markets(args):
    ms = fetch_markets(args.query or "", args.max)
    if not ms:
        print("Sin mercados que coincidan.")
        return
    print(f"\n{BOLD}Mercados abiertos{END} (vol 24h)")
    for m in ms:
        print(f"\n{BOLD}{m['question']}{END}  {DIM}vol {money(m['volume24hr'])}{END}")
        for o, p, t in zip(m["outcomes"], m["prices"], m["tokens"]):
            print(f"   {o:>4}  {p*100:5.1f}¢   {DIM}{t}{END}")


def cmd_price(args):
    bid = public_price(args.token_id, "sell")
    ask = public_price(args.token_id, "buy")
    print(f"compra (ask): {ask*100:.1f}¢   venta (bid): {bid*100:.1f}¢")


def cmd_positions(_):
    ps = fetch_positions(my_address())
    if not ps:
        print("Sin posiciones (o wallet vacía).")
        return
    print(f"\n{BOLD}Posiciones{END}")
    for p in ps:
        title = p.get("title") or p.get("market") or p.get("asset", "")[:18]
        size = float(p.get("size", 0))
        pnl = float(p.get("cashPnl", 0) or 0)
        col = GREEN if pnl >= 0 else RED
        print(f"  {str(title)[:46]:46}  {size:>8.2f} sh  P&L {col}{'+' if pnl>=0 else ''}{money(pnl)}{END}")


def cmd_balance(_):
    from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
    c = get_client()
    ba = c.get_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=SIG_TYPE or 0))
    bal = float(ba.get("balance", 0)) / 1e6
    allow = float(ba.get("allowance", 0)) / 1e6
    print(f"USDC disponible: {money(bal)}   allowance: {money(allow)}")
    if allow <= 0:
        print(f"{YEL}Allowance en 0 → corre 'python bot.py setup' antes de apostar.{END}")


def cmd_setup(_):
    from py_clob_client.clob_types import BalanceAllowanceParams, AssetType
    c = get_client()
    print("Aprobando USDC (allowance) para el exchange de Polymarket…")
    c.update_balance_allowance(BalanceAllowanceParams(asset_type=AssetType.COLLATERAL, signature_type=SIG_TYPE or 0))
    print(f"{GREEN}Listo.{END} Ya puedes apostar. (Esto es una tx on-chain de una sola vez.)")


def _place(c, token_id, side, usd=None, shares=None):
    from py_clob_client.clob_types import MarketOrderArgs, OrderType
    from py_clob_client.order_builder.constants import BUY, SELL
    amount = usd if side == "buy" else shares
    args = MarketOrderArgs(token_id=token_id, amount=float(amount), side=BUY if side == "buy" else SELL)
    order = c.create_market_order(args)
    return c.post_order(order, OrderType.FOK)


def confirm_live(yes):
    if yes:
        return
    a = input(f"{BOLD}{RED}DINERO REAL en Polymarket.{END} Escribe 'CONFIRMAR' para continuar: ")
    if a.strip() != "CONFIRMAR":
        sys.exit("Cancelado.")


def cmd_buy(args):
    confirm_live(args.yes)
    r = _place(get_client(), args.token_id, "buy", usd=args.usd)
    print(f"{GREEN}Compra enviada:{END} {money(args.usd)} → {r}")


def cmd_sell(args):
    confirm_live(args.yes)
    r = _place(get_client(), args.token_id, "sell", shares=args.shares)
    print(f"{RED}Venta enviada:{END} {args.shares} shares → {r}")


def build_plan():
    ms = fetch_markets(AB["query"], 60)
    plan, spent = [], 0.0
    for m in ms:
        if m["volume24hr"] < AB["min_volume"]:
            continue
        # elegir resultado segun la regla
        if AB["side"] == "yes":
            idx = 0
        elif AB["side"] == "no":
            idx = 1
        elif AB["side"] == "longshot":
            idx = min(range(len(m["prices"])), key=lambda i: m["prices"][i])
        else:  # favorite
            idx = max(range(len(m["prices"])), key=lambda i: m["prices"][i])
        price = m["prices"][idx]
        if not (AB["min_price"] <= price <= AB["max_price"]):
            continue
        if spent + AB["stake_usd"] > AB["budget_usd"]:
            break
        plan.append({"q": m["question"], "outcome": m["outcomes"][idx],
                     "price": price, "token": m["tokens"][idx], "stake": AB["stake_usd"]})
        spent += AB["stake_usd"]
        if len(plan) >= AB["max_bets"]:
            break
    return plan, spent


def cmd_autobet(args):
    print(f"{DIM}regla:{END} lado={AB['side']}  precio {AB['min_price']}-{AB['max_price']}  "
          f"${AB['stake_usd']}/apuesta  máx {AB['max_bets']}  presupuesto {money(AB['budget_usd'])}"
          + (f"  query='{AB['query']}'" if AB["query"] else ""))
    plan, spent = build_plan()
    if not plan:
        print(f"{YEL}Ningún mercado cumple la regla ahora mismo.{END} Ajusta AUTOBET_* en .env.")
        return
    print(f"\n{BOLD}Plan de apuestas{END} ({'EN VIVO' if args.live else 'SIMULACIÓN'})")
    for p in plan:
        gana = p["stake"] / p["price"] - p["stake"]
        print(f"  • {p['q'][:50]:50}  {p['outcome']:>4} @ {p['price']*100:.1f}¢  "
              f"apuesta {money(p['stake'])}  → si gana +{money(gana)}")
    print(f"  {DIM}total a arriesgar:{END} {money(spent)}")
    if not args.live:
        print(f"\n{YEL}Esto fue SIMULACIÓN.{END} Para apostar de verdad: python bot.py autobet --live")
        return
    confirm_live(args.yes)
    c = get_client()
    for p in plan:
        try:
            r = _place(c, p["token"], "buy", usd=p["stake"])
            print(f"  {GREEN}✓{END} {p['outcome']} @ {p['price']*100:.1f}¢  {money(p['stake'])} → {r}")
        except Exception as e:
            print(f"  {RED}✗{END} {p['q'][:40]}: {e}")


def main():
    p = argparse.ArgumentParser(description="polymarket-bot · apuestas con auto-bet")
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("markets"); m.add_argument("query", nargs="?", default="")
    m.add_argument("--max", type=int, default=15); m.set_defaults(func=cmd_markets)

    pr = sub.add_parser("price"); pr.add_argument("token_id"); pr.set_defaults(func=cmd_price)
    sub.add_parser("positions").set_defaults(func=cmd_positions)
    sub.add_parser("balance").set_defaults(func=cmd_balance)
    sub.add_parser("setup").set_defaults(func=cmd_setup)

    b = sub.add_parser("buy"); b.add_argument("token_id"); b.add_argument("--usd", type=float, required=True)
    b.add_argument("--yes", action="store_true"); b.set_defaults(func=cmd_buy)

    s = sub.add_parser("sell"); s.add_argument("token_id"); s.add_argument("--shares", type=float, required=True)
    s.add_argument("--yes", action="store_true"); s.set_defaults(func=cmd_sell)

    a = sub.add_parser("autobet"); a.add_argument("--live", action="store_true")
    a.add_argument("--yes", action="store_true"); a.set_defaults(func=cmd_autobet)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
