"""Costruisce il campione HeatDesk: unisce raccolta, arricchimento e verifiche,
calcola un punteggio a regole fisse e scrive il CSV e le schede per il BDR.

Uso: python3 -I costruisci_campione.py <cartella_dati>
"""
import csv
import os
import sys

D = sys.argv[1]
p = lambda n: os.path.join(D, n)

# --- 1. Lettura delle fonti -------------------------------------------------
cand = {r["id"]: r for r in csv.DictReader(open(p("candidati.csv")))}
arr = {}
for g in (1, 2, 3, 4):
    for r in csv.DictReader(open(p(f"gruppo{g}_output.csv"))):
        arr[r["id"]] = r
contatti = {}
for g in (5, 6):
    f = p(f"gruppo{g}_output.csv")
    if os.path.exists(f):
        for r in csv.DictReader(open(f)):
            contatti[r["id"]] = r
vies = {}
if os.path.exists(p("vies.csv")):
    for r in csv.DictReader(open(p("vies.csv"))):
        if r["vies_valida"] == "True":
            vies[r["id"]] = r
det = {}
for l in open(p("annunci_dettaglio.txt")):
    if l.startswith("#") or not l.strip():
        continue
    x = l.rstrip("\n").split("|")
    det[x[0]] = {"flag": set(filter(None, x[1].split(","))), "testo": x[2], "contatto": x[3]}

# --- 2. Decisioni prese a mano dopo la lettura degli annunci ----------------
REGIONE = {
    "1": "Lombardia", "2": "Lombardia", "3": "Lombardia", "4": "Lombardia", "5": "Sicilia",
    "6": "Lombardia", "7": "Friuli-Venezia Giulia", "8": "Emilia-Romagna", "9": "Lazio",
    "10": "Veneto", "11": "Friuli-Venezia Giulia", "12": "Veneto", "13": "Veneto",
    "14": "Lombardia", "15": "Lombardia", "16": "Emilia-Romagna", "17": "Emilia-Romagna",
    "18": "Veneto", "19": "Marche", "20": "Lombardia", "21": "Puglia", "22": "Molise",
    "23": "Lombardia", "24": "Lazio", "25": "Lombardia", "26": "Lombardia", "27": "Lombardia",
    "28": "Lombardia", "29": "Lombardia", "30": "Piemonte", "31": "Piemonte", "32": "Veneto",
    "33": "Veneto", "34": "Veneto", "35": "Lazio", "36": "Lazio", "37": "Lazio", "38": "Lazio",
    "39": "Lazio", "40": "Lazio", "41": "Toscana", "42": "Toscana", "43": "Toscana",
    "44": "Toscana", "45": "Piemonte", "46": "Lombardia", "47": "Veneto", "48": "Lombardia",
    "49": "Lombardia", "50": "Lombardia", "51": "Veneto", "52": "Veneto", "53": "Veneto",
    "54": "Emilia-Romagna", "55": "Lazio", "56": "Lazio", "57": "Lazio", "58": "Campania",
    "59": "Campania", "60": "Campania", "61": "Liguria",
}
SUD = {"Sicilia", "Puglia", "Molise", "Campania", "Calabria", "Basilicata", "Sardegna"}

FUORI = {
    "4": "rete nazionale di pronto intervento, non un installatore locale",
    "10": "manutenzione industriale in presidio presso un cliente",
    "22": "probabile rivenditore con 5 sedi (cerca commerciali)",
    "25": "piattaforma di selezione del personale",
    "26": "agenzia per il lavoro",
    "32": "distributore di materiale idrotermosanitario",
    "33": "refrigerazione industriale (macchinari)",
    "43": "troppo piccola (circa 0,2 M di fatturato)",
    "48": "troppo grande (42 addetti, 10,8 M)",
    "49": "bonifica legionella, non caldaie o clima",
    "50": "produzione di impianti di depurazione",
    "52": "manutenzione di macchinari industriali",
}
DUBBIO = {
    "21": "solo impianti su cantieri nuovi, nessuna manutenzione",
    "27": "manutenzione presso clienti; omonima non pertinente negli elenchi",
    "35": "impianti di alberghi e ospedali, profilo da facility",
    "36": "impiantistica ma ragione sociale da impresa edile",
    "38": "identità incerta: account 'Romana Appalti snc', testo 'Home Solution srls'",
    "39": "impiantistica e ristrutturazioni, manutenzione su commessa",
    "41": "impianti elettrici e termoidraulici; dimensione non nota",
    "42": "impianti tecnologici, non è chiaro se fa caldaie",
    "45": "cerca un magazziniere: forse rivendita",
    "47": "idraulica civile e industriale, nessun cenno a caldaie",
    "53": "idraulico ed elettricista, civile e industriale",
    "57": "annuncio non letto (verifica anti-bot di Indeed)",
    "58": "annuncio non letto; ditta individuale idraulica ed elettrica",
    "59": "annuncio non letto; cerca anche geometra: forse impresa più grande",
    "60": "annuncio non letto; edile e impiantista",
    "61": "annuncio non letto; elenchi la descrivono come fotovoltaico",
}
# Titolari ricavati dalla ragione sociale (ditte individuali e società di persone)
TITOLARE_DA_NOME = {
    "3": "soci Viganò (Walter, Elio, Roberto)",
    "12": "Ermir Pjetri",
    "15": "soci Figini e Azzoni",
    "24": "Mariano Cola",
    "31": "Massimo Pirazzoli",
    "54": "Morgan Covili",
}
PIU_ASSUNZIONI = {"1", "30", "39", "55"}  # più annunci o "diverse assunzioni"
# Ruoli d'ufficio o di coordinamento: il segnale più diretto del caos gestionale (pesa più dei tecnici)
RUOLO_UFFICIO = {"41": "controller di commessa / coordinatore operativo"}
RUOLO_COMMERCIALE = {"7": "tecnico commerciale"}
CAT_MARCHI = {
    "34": "Baxi, Viessmann, Toshiba, Stelbi, Wavin (dal sito); piani di manutenzione programmati",
    "3": "Unical, Daikin, Hoval, Cuenod",
    "20": "assistenza caldaie dal 1982, segue marchi (es. Sylber)",
    "23": "Clivet, Lennox, Loxone, Kessel",
}


# Correzioni dopo i controlli a campione sulle fonti (15/11/2026)
OVERRIDE = {
    # sito emmetermo.com: solo cellulare; il fisso veniva da Pagine Gialle e non è confermato.
    # Il titolare invece è confermato da VIES: "EMMETERMO DI LANCINI MARCO"
    "46": {"telefono_aziendale": "", "titolare": "Marco Lancini (ditta individuale, da VIES)"},
    # sede operativa dell'annuncio a Montemurlo, sede legale a Varese (numero verde: probabilmente più grande)
    "44": {"comune": "Montemurlo (sede operativa; sede legale Varese)"},
}


def num(x):
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return None


def pick(*vals):
    for v in vals:
        if v and str(v).strip():
            return str(v).strip()
    return ""


# --- 3. Fusione e punteggio --------------------------------------------------
righe = []
for i, c in cand.items():
    a = arr.get(i, {})
    k = contatti.get(i, {})
    d = det.get(i, {"flag": set(), "testo": "", "contatto": ""})
    f = d["flag"]
    regione = REGIONE[i]
    fatt = num(pick(k.get("fatturato_eur"), a.get("fatturato_eur")))
    dip = num(pick(k.get("dipendenti"), a.get("dipendenti")))
    ident = pick(k.get("identita_verificata") if k.get("identita_verificata") == "si" else "",
                 a.get("identita_verificata"))
    v = vies.get(i)
    if v:  # P.IVA confermata dal servizio VIES della Commissione europea
        ident = "si"
    tel = pick(k.get("telefono_aziendale"), a.get("telefono"))
    if not tel and "tel." in d["contatto"]:
        tel = d["contatto"].split("tel.")[1].strip()
    sito = pick(k.get("sito_web"), a.get("sito_web"))
    email = pick(k.get("email_generica"), a.get("email_generica"))
    if not email and "@" in d["contatto"] and d["contatto"].split()[0].lower().startswith(("info@", "amministrazione")):
        email = d["contatto"].split()[0]
    titolare = pick(k.get("titolare_o_amministratore"), a.get("titolare_o_amministratore"), TITOLARE_DA_NOME.get(i))
    marchi = pick(CAT_MARCHI.get(i), a.get("centro_assistenza_marchi"))
    ov = OVERRIDE.get(i, {})
    tel = ov.get("telefono_aziendale", tel)
    titolare = ov.get("titolare", titolare)

    if i in FUORI:
        verdetto, motivo = "fuori", FUORI[i]
    elif i in DUBBIO:
        verdetto, motivo = "dubbio", DUBBIO[i]
    else:
        verdetto, motivo = "dentro", "installa e/o mantiene caldaie o clima; piccola impresa"

    # Fit (max 45)
    s_fit = 0
    if "MANUT" in f and ({"CALD", "CLIMA"} & f):
        s_fit += 20
    elif {"CALD", "CLIMA"} & f:
        s_fit += 12
    if marchi:
        s_fit += 10
    in_fascia = (dip is not None and 5 <= dip <= 25) or (fatt is not None and 700_000 <= fatt <= 4_000_000)
    s_fit += 10 if in_fascia else (5 if dip is None and fatt is None else 0)
    s_fit += 0 if regione in SUD else 5
    # Momento e bisogno (max 40)
    s_tim = 15  # annuncio aperto negli ultimi 14 giorni
    s_tim += 5 if i in PIU_ASSUNZIONI else 0
    s_tim += 5 if "CRESCITA" in f else 0
    s_tim += 15 if i in RUOLO_UFFICIO else (5 if i in RUOLO_COMMERCIALE else 0)
    # Qualità e contattabilità (max 15)
    s_q = (5 if ident == "si" else 0) + (5 if (tel or sito) else 0) + (5 if titolare else 0)
    score = s_fit + s_tim + s_q
    if verdetto == "fuori":
        fascia = "esclusa"
    elif verdetto == "dubbio":
        fascia = "da verificare"
    else:
        fascia = "A" if score >= 70 else ("B" if score >= 55 else "C")

    righe.append({
        "id": i, "azienda": c["azienda"], "fascia": fascia, "punteggio": score if verdetto != "fuori" else "",
        "punti_fit": s_fit, "punti_momento": s_tim, "punti_qualita": s_q,
        "verdetto_icp": verdetto, "motivo": motivo,
        "regione": regione, "comune": ov.get("comune") or pick(k.get("comune_sede"), a.get("comune_sede"), c["luogo_annuncio"]),
        "ruolo_cercato": c["titoli_annunci"], "n_annunci": c["n_annunci"],
        "cosa_dice_annuncio": d["testo"],
        "segnali_nel_testo": ",".join(sorted(f)),
        "fa_caldaie": "si" if "CALD" in f else pick(a.get("fa_caldaie"), "nd"),
        "fa_clima_pdc": "si" if "CLIMA" in f else pick(a.get("fa_clima_pdc"), "nd"),
        "fa_manutenzione": "si" if "MANUT" in f else pick(a.get("fa_manutenzione_programmata"), "nd"),
        "centro_assistenza_marchi": marchi,
        "ragione_sociale": pick(v["vies_nome"] if v else "", k.get("ragione_sociale"), a.get("ragione_sociale_verificata")),
        "indirizzo_vies": v["vies_indirizzo"] if v else "",
        "piva": pick(k.get("piva"), a.get("piva")),
        "fatturato_eur": int(fatt) if fatt else "", "anno_fatturato": pick(k.get("anno_fatturato"), a.get("anno_fatturato")),
        "dipendenti": int(dip) if dip else "",
        "titolare": titolare, "sito_web": sito, "telefono_aziendale": tel, "email_generica": email,
        "identita_verificata": ident or "no",
        "link_annuncio": c["link_annuncio"],
        "fonti": " ".join(filter(None, [a.get("fonti", ""), k.get("fonti", ""),
                                        f"VIES {v['data_controllo']}" if v else ""])),
    })

ordine = {"A": 0, "B": 1, "C": 2, "da verificare": 3, "esclusa": 4}
righe.sort(key=lambda r: (ordine[r["fascia"]], -(r["punteggio"] or 0)))

with open(p("campione_heatdesk.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(righe[0].keys()))
    w.writeheader()
    w.writerows(righe)

# --- 4. Schede per il BDR (fasce A e B) --------------------------------------
def aggancio(r):
    ruolo = r["ruolo_cercato"].split(" / ")[0].strip().lower()
    if r["id"] in RUOLO_UFFICIO:
        return (f"Ho visto che cercate un {RUOLO_UFFICIO[r['id']]}. Oggi chi tiene l'agenda di tecnici, "
                f"interventi e manutenzioni, e con che strumento?")
    if r["centro_assistenza_marchi"]:
        return (f"Ho visto che cercate un {ruolo} e che fate assistenza su più marchi. "
                f"Quante manutenzioni programmate gestite all'anno, e dove le tenete oggi?")
    if "CRESCITA" in r["segnali_nel_testo"]:
        return (f"Ho visto che state ampliando la squadra ({ruolo}). Con un tecnico in più, "
                f"come organizzate oggi gli interventi e i richiami delle manutenzioni?")
    return (f"Ho visto che cercate un {ruolo}. Come gestite oggi l'agenda degli interventi "
            f"e le scadenze delle manutenzioni dei vostri clienti?")


with open(p("schede_bdr.md"), "w", encoding="utf-8") as fh:
    fh.write("# Schede pronte per il BDR (fasce A e B)\n\n")
    fh.write("Generate dal campione del 15/11/2026. Ogni scheda dice chi chiamare, perché adesso e con che frase aprire.\n\n")
    for r in righe:
        if r["fascia"] not in ("A", "B"):
            continue
        fh.write(f"## {r['azienda']} · fascia {r['fascia']} · {r['punteggio']} punti\n\n")
        fh.write(f"- Dove: {r['comune']} ({r['regione']})\n")
        fh.write(f"- Perché adesso: annuncio aperto su Indeed negli ultimi 14 giorni per {r['ruolo_cercato']}"
                 + (f" ({r['n_annunci']} annunci)" if r["n_annunci"] != "1" else "") + "\n")
        fh.write(f"- Cosa fanno (dall'annuncio): {r['cosa_dice_annuncio']}\n")
        if r["centro_assistenza_marchi"]:
            fh.write(f"- Centro assistenza: {r['centro_assistenza_marchi']}\n")
        dim = ", ".join(filter(None, [f"{r['dipendenti']} addetti" if r["dipendenti"] else "",
                                      f"{r['fatturato_eur']:,} € ({r['anno_fatturato']})".replace(",", ".") if r["fatturato_eur"] else ""]))
        fh.write(f"- Dimensione: {dim or 'non trovata con fonti gratuite'}\n")
        fh.write(f"- Chi chiedere: {r['titolare'] or 'il titolare (nome non trovato)'}\n")
        cont = ", ".join(filter(None, [r["telefono_aziendale"], r["email_generica"], r["sito_web"]]))
        fh.write(f"- Contatti aziendali: {cont or 'da cercare (non trovati gratis)'}\n")
        fh.write(f"- Frase di apertura: \"{aggancio(r)}\"\n")
        fh.write(f"- Annuncio: {r['link_annuncio']}\n")
        if r["identita_verificata"] != "si":
            fh.write("- Attenzione: identità non confermata da elenchi pubblici; prima di chiamare controlla sito e P.IVA\n")
        fh.write("\n")

# --- 5. Riepilogo -----------------------------------------------------------
from collections import Counter
cnt = Counter(r["fascia"] for r in righe)
print("fasce:", dict(cnt))
dentro = [r for r in righe if r["verdetto_icp"] == "dentro"]
for campo in ("piva", "sito_web", "telefono_aziendale", "fatturato_eur", "dipendenti", "titolare"):
    print(f"{campo}: {sum(1 for r in dentro if r[campo])}/{len(dentro)} (aziende dentro)")
print("identita si:", sum(1 for r in dentro if r["identita_verificata"] == "si"), "/", len(dentro))
print("identita si (tutte le 61):", sum(1 for r in righe if r["identita_verificata"] == "si"), "/", len(righe))
print("confermate da VIES:", sum(1 for r in righe if r["indirizzo_vies"]), "/", len(righe))
