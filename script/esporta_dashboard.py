"""Prepara i dati della dashboard BDR a partire dal campione.

Legge dati/campione_heatdesk.csv, ricava per ogni azienda i segnali che servono
a ricalcolare il punteggio (così i pesi si possono cambiare dalla dashboard),
scrive la frase di apertura e inserisce tutto in dashboard/template.html.

Uso: python3 -I script/esporta_dashboard.py <cartella_del_progetto>
"""
import csv
import json
import os
import sys

BASE = sys.argv[1]
SRC = os.path.join(BASE, "dati", "campione_heatdesk.csv")
TPL = os.path.join(BASE, "dashboard", "template.html")
OUT = os.path.join(BASE, "dashboard", "index.html")

# Stesse decisioni di costruisci_campione.py (lette a mano dagli annunci)
SUD = {"Sicilia", "Puglia", "Molise", "Campania", "Calabria", "Basilicata", "Sardegna"}
PIU_ASSUNZIONI = {"1", "30", "39", "55"}
RUOLO_UFFICIO = {"41": "controller di commessa / coordinatore operativo"}
RUOLO_COMMERCIALE = {"7"}


def num(x):
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return None


def aggancio(r, flags):
    ruolo = r["ruolo_cercato"].split(" / ")[0].strip().lower()
    if r["id"] in RUOLO_UFFICIO:
        return (f"Ho visto che cercate un {RUOLO_UFFICIO[r['id']]}. Oggi chi tiene l'agenda di tecnici, "
                f"interventi e manutenzioni, e con che strumento?")
    if r["centro_assistenza_marchi"]:
        return (f"Ho visto che cercate un {ruolo} e che fate assistenza su più marchi. "
                f"Quante manutenzioni programmate gestite all'anno, e dove le tenete oggi?")
    if "CRESCITA" in flags:
        return (f"Ho visto che state ampliando la squadra ({ruolo}). Con un tecnico in più, "
                f"come organizzate oggi gli interventi e i richiami delle manutenzioni?")
    return (f"Ho visto che cercate un {ruolo}. Come gestite oggi l'agenda degli interventi "
            f"e le scadenze delle manutenzioni dei vostri clienti?")


aziende = []
for r in csv.DictReader(open(SRC, encoding="utf-8")):
    f = set(filter(None, r["segnali_nel_testo"].split(",")))
    dip, fatt = num(r["dipendenti"]), num(r["fatturato_eur"])
    in_fascia = (dip is not None and 5 <= dip <= 25) or (fatt is not None and 700_000 <= fatt <= 4_000_000)
    aziende.append({
        "id": r["id"],
        "nome": r["azienda"],
        "ragione": r["ragione_sociale"],
        "fascia": r["fascia"],
        "verdetto": r["verdetto_icp"],
        "motivo": r["motivo"],
        "regione": r["regione"],
        "comune": r["comune"],
        "ruolo": r["ruolo_cercato"],
        "nAnnunci": int(r["n_annunci"] or 1),
        "testo": r["cosa_dice_annuncio"],
        "marchi": r["centro_assistenza_marchi"],
        "piva": r["piva"],
        "vies": r["indirizzo_vies"],
        "fatturato": int(fatt) if fatt else None,
        "annoFatt": r["anno_fatturato"],
        "dipendenti": int(dip) if dip else None,
        "titolare": r["titolare"],
        "sito": r["sito_web"],
        "tel": r["telefono_aziendale"],
        "email": r["email_generica"],
        "link": r["link_annuncio"],
        "fonti": r["fonti"],
        "apertura": aggancio(r, f),
        # segnali per ricalcolare il punteggio con pesi diversi
        "s": {
            "manut": "MANUT" in f and bool({"CALD", "CLIMA"} & f),
            "install": bool({"CALD", "CLIMA"} & f),
            "marchi": bool(r["centro_assistenza_marchi"]),
            "inFascia": in_fascia,
            "dimNota": dip is not None or fatt is not None,
            "nordCentro": r["regione"] not in SUD,
            "ufficio": r["id"] in RUOLO_UFFICIO,
            "commerciale": r["id"] in RUOLO_COMMERCIALE,
            "piuAssunzioni": r["id"] in PIU_ASSUNZIONI,
            "crescita": "CRESCITA" in f,
            "identita": r["identita_verificata"] == "si",
            "contatto": bool(r["telefono_aziendale"] or r["sito_web"]),
            "titolare": bool(r["titolare"]),
        },
        "puntiCsv": int(r["punteggio"]) if r["punteggio"] else None,
    })

html = open(TPL, encoding="utf-8").read()
dati = json.dumps(aziende, ensure_ascii=False, separators=(",", ":"))
html = html.replace("/*__DATI__*/[]", dati)
open(OUT, "w", encoding="utf-8").write(html)
print(f"{len(aziende)} aziende scritte in {OUT}")
