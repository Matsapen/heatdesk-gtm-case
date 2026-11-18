"""Controlla le partite IVA del campione sul servizio pubblico gratuito VIES
della Commissione europea (per l'Italia restituisce ragione sociale e indirizzo).

Uso: python3 -I verifica_vies.py <campione.csv> <output.csv>
"""
import csv
import json
import sys
import time
import urllib.request

src, out = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(src, encoding="utf-8")))
res = []
for r in rows:
    piva = "".join(ch for ch in r.get("piva", "") if ch.isdigit())
    if len(piva) != 11:
        continue
    url = f"https://ec.europa.eu/taxation_customs/vies/rest-api/ms/IT/vat/{piva}"
    try:
        with urllib.request.urlopen(url, timeout=20) as fh:
            d = json.load(fh)
        res.append({"id": r["id"], "azienda": r["azienda"], "piva": piva,
                    "vies_valida": d.get("isValid"), "vies_nome": d.get("name", ""),
                    "vies_indirizzo": " ".join(d.get("address", "").split()),
                    "data_controllo": d.get("requestDate", "")[:10]})
    except Exception as e:  # servizio non disponibile: si annota, non si inventa
        res.append({"id": r["id"], "azienda": r["azienda"], "piva": piva,
                    "vies_valida": "errore", "vies_nome": "", "vies_indirizzo": str(e)[:80],
                    "data_controllo": ""})
    time.sleep(1.5)  # ritmo lento, servizio pubblico

with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(res[0].keys()))
    w.writeheader()
    w.writerows(res)
for x in res:
    print(x["id"], x["azienda"][:28], "|", x["vies_valida"], "|", x["vies_nome"][:40], "|", x["vies_indirizzo"][:60])
