# -*- coding: utf-8 -*-
"""Modelo estadístico de valor para Polymarket (selección + sizing).

Idea honesta: el precio de un mercado YA es la probabilidad que le asigna la
multitud, y suele ser bastante eficiente. Para apostar con ventaja necesitas una
probabilidad "verdadera" distinta del precio. Aquí esa estimación sale de
recalibrar el precio para corregir el sesgo favorito-longshot (un sesgo empírico
documentado: los longshots suelen estar sobrevaluados y los favoritos algo
subvaluados). Con esa probabilidad estimamos la ventaja y el tamaño de apuesta
con el criterio de Kelly (fracción configurable, por seguridad usamos Kelly/4).

NO garantiza ganar: la ventaja es pequeña y discutible, y las comisiones/spread
pueden comérsela. Es un marco disciplinado de sizing, no dinero gratis.
"""
import math
import argparse
import requests

GAMMA = "https://gamma-api.polymarket.com"
G, R, DIM, B, Y, E = "\033[92m", "\033[91m", "\033[2m", "\033[1m", "\033[93m", "\033[0m"


def jload(s, d):
    import json
    try:
        return json.loads(s) if isinstance(s, str) else (s or d)
    except Exception:
        return d


def fetch_markets(min_vol, query=""):
    r = requests.get(f"{GAMMA}/markets", params={
        "closed": "false", "active": "true", "limit": 400,
        "order": "volume24hr", "ascending": "false"}, timeout=30)
    r.raise_for_status()
    out = []
    for m in r.json():
        q = m.get("question") or ""
        if query and query.lower() not in q.lower():
            continue
        toks = jload(m.get("clobTokenIds"), [])
        outs = jload(m.get("outcomes"), [])
        prices = [float(p) for p in jload(m.get("outcomePrices"), [])]
        vol = float(m.get("volume24hr") or 0)
        if len(toks) != 2 or len(prices) != 2 or vol < min_vol:
            continue
        ev = (m.get("events") or [{}])[0]
        slug = ev.get("slug") or m.get("slug")
        url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"
        out.append({"q": q, "outcomes": outs, "prices": prices, "tokens": toks,
                    "vol": vol, "url": url})
    return out


def logit(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def recalibrate(price, k):
    """Probabilidad 'verdadera' estimada: empuja los extremos (k>1) para
    corregir el sesgo favorito-longshot."""
    return sigmoid(k * logit(price))


def kelly_fraction(p, c):
    """Fracción óptima de banca al comprar a precio c con prob. verdadera p.
    Comprar a c paga 1 si acierta: f* = (p - c) / (1 - c)."""
    return (p - c) / (1 - c) if p > c else 0.0


def analyze(markets, bankroll, k, kfrac, max_bet_frac, min_edge, lo, hi):
    recs = []
    for m in markets:
        best = None
        for out, c, tok in zip(m["outcomes"], m["prices"], m["tokens"]):
            if not (lo <= c <= hi):
                continue
            p = recalibrate(c, k)
            edge = p - c
            if edge < min_edge:
                continue
            f = kelly_fraction(p, c) * kfrac
            stake = min(f * bankroll, max_bet_frac * bankroll)
            if stake < 1:
                continue
            cand = {"q": m["q"], "side": out, "price": c, "p": p, "edge": edge,
                    "stake": stake, "w": f, "tok": tok, "vol": m["vol"], "url": m["url"]}
            if best is None or cand["edge"] > best["edge"]:
                best = cand
        if best:
            recs.append(best)
    recs.sort(key=lambda r: r["edge"], reverse=True)
    return recs


def main():
    ap = argparse.ArgumentParser(description="Modelo de valor + Kelly para Polymarket")
    ap.add_argument("--bankroll", type=float, default=136.0)
    ap.add_argument("--k", type=float, default=1.15, help="fuerza de recalibración (>1)")
    ap.add_argument("--kelly-frac", type=float, default=0.25, help="fracción de Kelly (0.25 = Kelly/4)")
    ap.add_argument("--max-bet", type=float, default=0.10, help="tope por apuesta (fracción de banca)")
    ap.add_argument("--min-edge", type=float, default=0.012, help="ventaja mínima para apostar")
    ap.add_argument("--lo", type=float, default=0.60, help="precio mínimo del lado a apostar")
    ap.add_argument("--hi", type=float, default=0.95, help="precio máximo (evita casi-seguros)")
    ap.add_argument("--min-vol", type=float, default=50000)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--query", default="")
    ap.add_argument("--deploy-all", action="store_true", help="reparte TODA la banca entre las apuestas")
    ap.add_argument("--spread", type=int, default=10, help="nº de apuestas al usar --deploy-all")
    a = ap.parse_args()

    ms = fetch_markets(a.min_vol, a.query)
    n = a.spread if a.deploy_all else a.top
    recs = analyze(ms, a.bankroll, a.k, a.kelly_frac, a.max_bet, a.min_edge, a.lo, a.hi)[:n]
    if not recs:
        print(f"{Y}Ningún mercado supera el filtro ahora.{E} Baja --min-edge o --min-vol.")
        return

    if a.deploy_all:
        # escala las apuestas (proporcional al peso de Kelly) para sumar la banca
        tot_w = sum(r["w"] for r in recs) or 1.0
        for r in recs:
            r["stake"] = a.bankroll * r["w"] / tot_w

    print(f"\n{B}Plan estadístico (banca {a.bankroll:.0f} USD · Kelly/{1/a.kelly_frac:.0f}){E}")
    print(f"{DIM}recalibración k={a.k} · ventaja mín {a.min_edge*100:.1f}% · tope {a.max_bet*100:.0f}%/apuesta{E}\n")
    total = 0.0
    for i, r in enumerate(recs, 1):
        total += r["stake"]
        gana = r["stake"] / r["price"] - r["stake"]
        print(f"{B}{i}. {r['q'][:60]}{E}")
        print(f"   apostar {G}{r['side']}{E} @ {r['price']*100:.1f}¢   "
              f"prob. mercado {r['price']*100:.0f}% → estimada {r['p']*100:.0f}%   "
              f"ventaja {G}+{r['edge']*100:.1f}%{E}")
        print(f"   {B}meter ${r['stake']:.2f}{E}  → si gana +${gana:.2f}  "
              f"{DIM}(vol 24h ${r['vol']:,.0f}){E}")
        print(f"   {DIM}{r['url']}{E}\n")
    print(f"{B}Total a desplegar: ${total:.2f}{E} de ${a.bankroll:.0f}  "
          f"({DIM}deja ${a.bankroll-total:.2f} en reserva{E})")
    print(f"\n{Y}Recuerda:{E} esto explota un sesgo pequeño y discutible; las comisiones/spread "
          f"pueden borrar la ventaja. Es sizing disciplinado, no ganancia segura.")


if __name__ == "__main__":
    main()
