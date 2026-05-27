import json
import requests
from datetime import datetime, timedelta

LATITUDE = "42.7917"   
LONGITUDE = "14.1250"  
FORECAST_DAYS = "4"    

URL = f"https://marine-api.open-meteo.com/v1/marine?latitude={LATITUDE}&longitude={LONGITUDE}&minutely_15=sea_level_height_msl&timezone=Europe/Rome&forecast_days={FORECAST_DAYS}"

print("📡 Connessione all'API di Open-Meteo...")
response = requests.get(URL)

if response.status_code != 200:
    print(f"❌ Errore API: {response.status_code}")
    exit(1)

data = response.json()
orari_api = data["minutely_15"]["time"]
livelli_api = data["minutely_15"]["sea_level_height_msl"]

risultati_finali = []
tendenza_attuale = None
indici_stessa_tendenza = []

if len(livelli_api) > 0:
    risultati_finali.append({
        "idx": 0, "data_ora": orari_api[0].replace("T", " "), "livello": livelli_api[0],
        "stato": "INIZIO", "tendenza": "NESSUNA", "picco": "-"
    })
    indici_stessa_tendenza.append(0)

for i in range(1, len(livelli_api)):
    prec = livelli_api[i-1]
    curr = livelli_api[i]
    data_ora_str = orari_api[i].replace("T", " ")
    
    if prec is None or curr is None:
        risultati_finali.append({
            "idx": i, "data_ora": data_ora_str, "livello": "Nullo",
            "stato": "-", "tendenza": "-", "picco": "-"
        })
        continue

    if curr == prec:
        stato = "FLESSO"
    elif curr > prec:
        stato = "AUMENTO"
    else:
        stato = "DIMINUZIONE"

    tendenza_riga = stato if stato != "FLESSO" else (tendenza_attuale if tendenza_attuale else "NESSUNA")

    risultati_finali.append({
        "idx": i, "data_ora": data_ora_str, "livello": curr,
        "stato": stato, "tendenza": tendenza_riga, "picco": "-"
    })

    if stato != "FLESSO":
        nuova_tendenza = stato
        
        if tendenza_attuale is not None and nuova_tendenza != tendenza_attuale:
            tipo_picco = "👑 ALTA MAREA" if nuova_tendenza == "DIMINUZIONE" else "⚓ BASSA MAREA"
            
            valori_ciclo_precedente = [livelli_api[idx] for idx in indici_stessa_tendenza if livelli_api[idx] is not None]
            
            if valori_ciclo_precedente:
                estremo_raggiunto = max(valori_ciclo_precedente) if nuova_tendenza == "DIMINUZIONE" else min(valori_ciclo_precedente)
                indici_plateau = [idx for idx in indici_stessa_tendenza if livelli_api[idx] == estremo_raggiunto]
                
                if indici_plateau:
                    idx_inizio = indici_plateau[0]
                    idx_fine = indici_plateau[-1]
                    idx_centro = idx_inizio + ((idx_fine - idx_inizio) // 2)
                    
                    risultati_finali[idx_centro]["picco"] = tipo_picco
            
            indici_stessa_tendenza = []
            
        tendenza_attuale = nueva_tendenza

    indici_stessa_tendenza.append(i)

json_filtrato = []

# Costruzione del file iCalendar (.ics) standard
ics_lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Maree Bot//Controllo Maree//IT",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Controllo Maree",
    "X-WR-TIMEZONE:Europe/Rome"
]

contatore = 0
for riga in risultati_finali:
    if riga["picco"] != "-":
        json_filtrato.append({
            "data_ora": riga["data_ora"],
            "picco": riga["picco"]
        })
        
        dt_inizio = datetime.strptime(riga["data_ora"], "%Y-%m-%d %H:%M")
        dt_fine = dt_inizio + timedelta(minutes=30)
        
        emoji = "👑" if "ALTA" in riga["picco"] else "⚓"
        nome_marea = "Alta Marea" if "ALTA" in riga["picco"] else "Bassa Marea"
        
        # Formato data iCalendar: YYYYMMDDTHMMSS
        stamp_ora = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        str_inizio = dt_inizio.strftime("%Y%m%dT%H%M%S")
        str_fine = dt_fine.strftime("%Y%m%dT%H%M%S")
        
        contatore += 1
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:marea_2026_{contatore}@controllo_maree",
            f"DTSTAMP:{stamp_ora}",
            f"DTSTART;TZID=Europe/Rome:{str_inizio}",
            f"DTEND;TZID=Europe/Rome:{str_fine}",
            f"SUMMARY:{emoji} {nome_marea} ({riga['livello']} m)",
            f"DESCRIPTION:Picco reale calcolato al centro del flesso. Livello: {riga['livello']} m MSL.",
            "END:VEVENT"
        ])

ics_lines.append("END:VCALENDAR")

# Salva il file JSON
with open("maree_picchi.json", "w", encoding="utf-8") as f:
    json.dump(json_filtrato, f, ensure_ascii=False, indent=4)

# Salva il file iCalendar (.ics)
with open("maree_calendar.ics", "w", encoding="utf-8") as f:
    f.write("\n".join(ics_lines))

print(f"✅ Calendario .ics generato con successo alle {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")