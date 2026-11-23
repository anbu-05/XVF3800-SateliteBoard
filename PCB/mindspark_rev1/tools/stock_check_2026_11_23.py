"""LCSC stock check for the JLC BOM (pre-order step 6, 2026-11-23).

Usage:
    python3 tools/stock_check_2026_11_23.py [boards]      # default 2 (user: 5 made, 2 assembled)

Reads fab/JLCPCB_rev1/assembly/mindspark_rev1_BOM_JLC.csv, asks LCSC's public product API for
each part's stock and price, and writes bom/stock-2026-11-23.md (a table with a link to every
part page checked). JLC's own assembly stock is shown by JLC when the BOM is uploaded; LCSC
stock is what JLC can pre-order from if its shelf runs short.
A line is flagged when neither LCSC nor JLC's own shelf holds the parts needed x 2 (JLC also
adds a few extra pieces of small passives for attrition) or the part is not orderable.
Since 2026-11-23 JLC's shelf stock is read too (JLC's public parts search, the same numbers the
order's BOM step shows): some parts JLC assembles are not listed on LCSC at all (the Knowles
SPH0641LM4H-1 mic, C497724), and JLC places from its shelf first.
"""
import csv
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.join(HERE, "..")
BOM = os.path.join(PRJ, "fab", "JLCPCB_rev1", "assembly", "mindspark_rev1_BOM_JLC.csv")
OUT = os.path.join(PRJ, "bom", "stock-2026-11-23.md")
API = "https://wmsc.lcsc.com/ftps/wm/product/detail?productCode="


def fetch(code):
    req = urllib.request.Request(API + code, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r).get("result") or {}


JLC_API = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"


def fetch_jlc(code):
    """JLC shelf stock for an LCSC part number (None if JLC does not list it)."""
    body = json.dumps({"keyword": code, "currentPage": 1, "pageSize": 10}).encode()
    req = urllib.request.Request(JLC_API, data=body, headers={"Content-Type": "application/json",
                                                              "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        lst = ((json.load(r).get("data") or {}).get("componentPageInfo") or {}).get("list") or []
    hit = [p for p in lst if p.get("componentCode") == code]
    return hit[0].get("stockCount") if hit else None


def unit_price(res, qty):
    """Price per piece at the ladder step that covers qty (or the smallest step)."""
    ladder = sorted(res.get("productPriceList") or [], key=lambda p: p["ladder"])
    if not ladder:
        return None
    pick = ladder[0]
    for p in ladder:
        if p["ladder"] <= qty:
            pick = p
    return float(pick["usdPrice"])


def main(boards):
    rows = list(csv.DictReader(open(BOM)))
    out, flagged, total = [], [], 0.0
    for r in rows:
        code = r["LCSC Part #"]
        per_board = len(r["Designator"].split(","))
        need = per_board * boards
        try:
            res = fetch(code)
        except Exception as e:              # network hiccup: report it, don't guess
            res = {"error": str(e)}
        try:
            jlc = fetch_jlc(code)
        except Exception:                   # network hiccup: shown as '-'
            jlc = None
        time.sleep(0.3)
        stock = res.get("stockNumber")
        minbuy = res.get("minBuyNumber") or 1
        price = unit_price(res, max(need, minbuy))
        cost = price * max(need, minbuy) if price is not None else None
        total += cost or 0.0
        link = f"[{code}](https://www.lcsc.com/product-detail/{code}.html)"
        flag = ""
        best = max(stock or 0, jlc or 0)
        if stock is None and jlc is None:
            flag = "NOT FOUND" if "error" not in res else "CHECK FAILED"
        elif best < need * 2:
            flag = "LOW"
        if flag:
            flagged.append(f"{code} {r['Comment']} ({flag}, LCSC {stock}, JLC {jlc}, need {need})")
        out.append(f"| {r['Comment']} | {r['Designator'] if per_board <= 4 else r['Designator'].split(',')[0] + ' … (' + str(per_board) + ')'} "
                   f"| {link} | {res.get('productModel', r['Comment'])} | {need} | {stock if stock is not None else '-'} "
                   f"| {jlc if jlc is not None else '-'} "
                   f"| {minbuy} | {f'{cost:.2f}' if cost is not None else '?'} | {flag} |")
        print(f"{code:>10} need {need:>4} LCSC {stock} JLC {jlc} {flag}")

    with open(OUT, "w") as f:
        f.write(f"# LCSC stock check 2026-11-23 ({boards} assembled boards)\n\n")
        f.write("From LCSC's product API (each part page linked) for every line of the JLC BOM "
                "(`fab/JLCPCB_rev1/assembly/mindspark_rev1_BOM_JLC.csv`). Need = parts per board x "
                f"{boards}. Cost = LCSC price at the min-buy or needed quantity, parts only "
                "(JLC assembly fees, extended-part fees and attrition extras not included). "
                "JLC stock = JLC's own assembly shelf (its parts search); '-' = not listed there. "
                "LOW = neither stock covers 2 x need.\n\n")
        f.write("| Value | Refs | LCSC | MPN | Need | LCSC stock | JLC stock | Min buy | Cost $ | Flag |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        f.write("\n".join(out) + "\n\n")
        f.write(f"Parts total at LCSC prices: about ${total:.2f} for {boards} boards.\n\n")
        f.write("Flagged: " + ("; ".join(flagged) if flagged else "none") + "\n")
    print(f"total ${total:.2f}; flagged: {flagged or 'none'}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
