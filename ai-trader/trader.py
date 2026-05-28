# -*- coding: utf-8 -*-
"""ai-trader — a real trading bot wired to Alpaca (a regulated broker).

Your money lives in YOUR Alpaca account; this script only talks to Alpaca's
REST API with your keys. It defaults to PAPER (practice money). To trade real
money you set ALPACA_PAPER=false in .env and use live keys from a funded
account. Live orders ask for one confirmation (skip with --yes).

Commands:
  python trader.py account                 account summary + buying power
  python trader.py positions               open positions with P&L
  python trader.py quote AAPL              latest price (via yfinance)
  python trader.py buy AAPL --usd 200      market buy $200 (notional)
  python trader.py buy AAPL --qty 3        market buy 3 shares
  python trader.py sell AAPL --qty 3       market sell 3 shares
  python trader.py close AAPL              close the whole position
  python trader.py strategy                rank the universe, show the plan (dry run)
  python trader.py invest --usd 1000       split $1000 across the top picks
  python trader.py rebalance --usd 1000    close non-picks, then invest in picks

NOT financial advice. Trading real money can lose money.
"""
import os
import sys
import math
import argparse

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

# ----- config -----
KEY = os.getenv("ALPACA_KEY", "")
SECRET = os.getenv("ALPACA_SECRET", "")
PAPER = os.getenv("ALPACA_PAPER", "true").strip().lower() not in ("false", "0", "no")
TOP_N = int(os.getenv("TRADER_TOP_N", "4"))
# Universe to score & trade. Override with TRADER_UNIVERSE="AAPL,MSFT,...".
UNIVERSE = [s.strip().upper() for s in os.getenv(
    "TRADER_UNIVERSE", "AAPL,MSFT,NVDA,GOOGL,META,AMZN,TSLA").split(",") if s.strip()]

BASE = "https://paper-api.alpaca.markets" if PAPER else "https://api.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SECRET, "accept": "application/json"}

GREEN, RED, DIM, BOLD, END = "\033[92m", "\033[91m", "\033[2m", "\033[1m", "\033[0m"


def money(v):
    v = float(v)
    return ("-$" if v < 0 else "$") + f"{abs(v):,.2f}"


def signed(v):
    v = float(v)
    return ("+" if v > 0 else "-" if v < 0 else "") + "$" + f"{abs(v):,.2f}"


def color(v, text=None):
    text = text if text is not None else str(v)
    return f"{GREEN}{text}{END}" if float(v) > 0 else f"{RED}{text}{END}" if float(v) < 0 else text


# ----- Alpaca REST client -----
class Alpaca:
    def __init__(self):
        if not KEY or not SECRET:
            sys.exit(f"{RED}Falta configurar tus llaves.{END} Copia .env.example a .env y pon ALPACA_KEY / ALPACA_SECRET.\n"
                     "Llaves gratis (paper): https://alpaca.markets/")

    def _req(self, method, path, **kw):
        r = requests.request(method, BASE + path, headers=HEADERS, timeout=30, **kw)
        if r.status_code >= 400:
            msg = r.text
            try:
                msg = r.json().get("message", msg)
            except Exception:
                pass
            raise SystemExit(f"{RED}Error Alpaca {r.status_code}:{END} {msg}")
        return r.json() if r.text else {}

    def account(self):
        return self._req("GET", "/v2/account")

    def positions(self):
        return self._req("GET", "/v2/positions")

    def close_position(self, symbol):
        return self._req("DELETE", f"/v2/positions/{symbol}")

    def order(self, symbol, side, usd=None, qty=None):
        body = {"symbol": symbol, "side": side, "type": "market", "time_in_force": "day"}
        if usd is not None:
            body["notional"] = round(float(usd), 2)
        else:
            body["qty"] = qty
        return self._req("POST", "/v2/orders", json=body)


# ----- market data / strategy (yfinance) -----
def _yf():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        sys.exit(f"{RED}Falta yfinance.{END} Corre: pip install -r requirements.txt")


def last_price(symbol):
    t = _yf().Ticker(symbol)
    try:
        p = t.fast_info.get("last_price")
        if p:
            return float(p)
    except Exception:
        pass
    h = t.history(period="1d")
    return float(h["Close"].iloc[-1]) if len(h) else None


def _norm(vals, higher_better=True):
    nums = [v for v in vals if v is not None]
    if not nums:
        return [0.5] * len(vals)
    lo, hi = min(nums), max(nums)
    out = []
    for v in vals:
        if v is None or hi == lo:
            out.append(0.5)
        else:
            s = (v - lo) / (hi - lo)
            out.append(s if higher_better else 1 - s)
    return out


def score_universe(universe=None):
    """Rank tickers by a transparent fundamental score (0-100)."""
    yf = _yf()
    universe = universe or UNIVERSE
    rows = []
    for tk in universe:
        info = {}
        try:
            info = yf.Ticker(tk).info
        except Exception:
            pass
        rows.append({
            "ticker": tk,
            "pe": info.get("forwardPE") or info.get("trailingPE"),
            "rev": info.get("revenueGrowth"),
            "earn": info.get("earningsGrowth"),
            "roe": info.get("returnOnEquity"),
            "margin": info.get("profitMargins"),
        })
    factors = [("pe", False, 0.25), ("rev", True, 0.20), ("earn", True, 0.15),
               ("roe", True, 0.22), ("margin", True, 0.18)]
    comp = {r["ticker"]: 0.0 for r in rows}
    for key, hb, w in factors:
        ns = _norm([r[key] for r in rows], hb)
        for r, n in zip(rows, ns):
            comp[r["ticker"]] += n * w
    for r in rows:
        r["score"] = round(comp[r["ticker"]] * 100, 1)
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


# ----- helpers -----
def confirm_live(yes):
    if PAPER or yes:
        return
    ans = input(f"{BOLD}{RED}Esto usa DINERO REAL en tu cuenta Alpaca.{END} Escribe 'CONFIRMAR' para continuar: ")
    if ans.strip() != "CONFIRMAR":
        sys.exit("Cancelado.")


def mode_banner():
    tag = f"{GREEN}PAPER (práctica){END}" if PAPER else f"{RED}REAL (dinero de verdad){END}"
    print(f"{DIM}modo:{END} {tag}   {DIM}universo:{END} {', '.join(UNIVERSE)}")


# ----- commands -----
def cmd_account(_):
    a = Alpaca().account()
    print(f"\n{BOLD}Cuenta{END}  ({a.get('status', '?')})")
    print(f"  Valor de cartera : {money(a['portfolio_value'])}")
    print(f"  Efectivo         : {money(a['cash'])}")
    print(f"  Poder de compra  : {money(a['buying_power'])}")


def cmd_positions(_):
    ps = Alpaca().positions()
    if not ps:
        print("Sin posiciones abiertas.")
        return
    print(f"\n{BOLD}Posiciones{END}")
    total = 0.0
    for p in ps:
        pl = float(p["unrealized_pl"])
        total += pl
        plpc = float(p["unrealized_plpc"]) * 100
        print(f"  {p['symbol']:6} {float(p['qty']):>8.3f} @ {money(p['avg_entry_price'])}"
              f"  valor {money(p['market_value'])}  P&L {color(pl, signed(pl))} ({color(pl, f'{plpc:+.1f}%')})")
    print(f"  {DIM}P&L no realizado total:{END} {color(total, signed(total))}")


def cmd_quote(args):
    p = last_price(args.symbol.upper())
    print(f"{args.symbol.upper()}: {money(p) if p else 'n/d'}")


def cmd_buy(args):
    confirm_live(args.yes)
    o = Alpaca().order(args.symbol.upper(), "buy", usd=args.usd, qty=args.qty)
    print(f"{GREEN}Orden enviada:{END} BUY {args.symbol.upper()} "
          f"{('$' + str(args.usd)) if args.usd else (str(args.qty) + ' acc.')} → id {o.get('id', '?')[:8]} ({o.get('status')})")


def cmd_sell(args):
    confirm_live(args.yes)
    o = Alpaca().order(args.symbol.upper(), "sell", usd=args.usd, qty=args.qty)
    print(f"{RED}Orden enviada:{END} SELL {args.symbol.upper()} "
          f"{('$' + str(args.usd)) if args.usd else (str(args.qty) + ' acc.')} → id {o.get('id', '?')[:8]} ({o.get('status')})")


def cmd_close(args):
    confirm_live(args.yes)
    o = Alpaca().close_position(args.symbol.upper())
    print(f"Cerrando posición {args.symbol.upper()} → id {o.get('id', '?')[:8]} ({o.get('status')})")


def print_ranking(rows, picks):
    print(f"\n{BOLD}Ranking fundamental{END}")
    for i, r in enumerate(rows):
        star = f"{GREEN}★ pick{END}" if r["ticker"] in picks else ""
        pe = f"{r['pe']:.1f}" if r["pe"] else "n/d"
        print(f"  #{i+1} {r['ticker']:6} score {r['score']:>5.1f}   P/E {pe:>6}   {star}")


def cmd_strategy(_):
    mode_banner()
    rows = score_universe()
    picks = [r["ticker"] for r in rows[:TOP_N]]
    print_ranking(rows, picks)
    print(f"\n{BOLD}Plan (dry run):{END} invertir por igual en {picks}")
    print(f"{DIM}Ejecuta con: python trader.py invest --usd <monto>{END}")


def cmd_invest(args):
    mode_banner()
    confirm_live(args.yes)
    rows = score_universe()
    picks = [r["ticker"] for r in rows[:TOP_N]]
    print_ranking(rows, picks)
    per = round(args.usd / len(picks), 2)
    print(f"\nInvirtiendo {money(args.usd)} → {money(per)} en cada uno de {picks}")
    api = Alpaca()
    for tk in picks:
        try:
            o = api.order(tk, "buy", usd=per)
            print(f"  {GREEN}✓{END} BUY {tk} {money(per)} → {o.get('status')}")
        except SystemExit as e:
            print(f"  {RED}✗{END} {tk}: {e}")


def cmd_rebalance(args):
    mode_banner()
    confirm_live(args.yes)
    rows = score_universe()
    picks = [r["ticker"] for r in rows[:TOP_N]]
    print_ranking(rows, picks)
    api = Alpaca()
    held = {p["symbol"]: p for p in api.positions()}
    for sym in held:
        if sym not in picks:
            print(f"  {RED}cerrando{END} {sym} (fuera de picks)")
            try:
                api.close_position(sym)
            except SystemExit as e:
                print(f"    {RED}✗{END} {e}")
    per = round(args.usd / len(picks), 2)
    print(f"Invirtiendo {money(args.usd)} → {money(per)} en cada pick")
    for tk in picks:
        try:
            o = api.order(tk, "buy", usd=per)
            print(f"  {GREEN}✓{END} BUY {tk} {money(per)} → {o.get('status')}")
        except SystemExit as e:
            print(f"  {RED}✗{END} {tk}: {e}")


def main():
    p = argparse.ArgumentParser(description="ai-trader · bot de trading sobre Alpaca")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("account").set_defaults(func=cmd_account)
    sub.add_parser("positions").set_defaults(func=cmd_positions)

    q = sub.add_parser("quote"); q.add_argument("symbol"); q.set_defaults(func=cmd_quote)

    for name, fn in (("buy", cmd_buy), ("sell", cmd_sell)):
        s = sub.add_parser(name)
        s.add_argument("symbol")
        s.add_argument("--usd", type=float, help="monto en dólares (orden notional)")
        s.add_argument("--qty", type=float, help="número de acciones")
        s.add_argument("--yes", action="store_true", help="omitir confirmación en modo real")
        s.set_defaults(func=fn)

    c = sub.add_parser("close"); c.add_argument("symbol")
    c.add_argument("--yes", action="store_true"); c.set_defaults(func=cmd_close)

    sub.add_parser("strategy").set_defaults(func=cmd_strategy)

    for name, fn in (("invest", cmd_invest), ("rebalance", cmd_rebalance)):
        s = sub.add_parser(name)
        s.add_argument("--usd", type=float, required=True, help="capital total a repartir")
        s.add_argument("--yes", action="store_true")
        s.set_defaults(func=fn)

    args = p.parse_args()
    # validate buy/sell amount
    if args.cmd in ("buy", "sell") and args.usd is None and args.qty is None:
        sys.exit("Especifica --usd <monto> o --qty <acciones>.")
    args.func(args)


if __name__ == "__main__":
    main()
