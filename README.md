# G4MEOVER Companion Tools

PC-Begleitwerkzeuge für das G4MEOVER-Flipper-Ökosystem. Reine Test-/Forschungswerkzeuge für eigene Geräte / autorisierte Tests.

## Tools

### magtool (`magtool/magtool.py`)
Baut, validiert und liest `.mag`-Dateien für die G4MEOVER-MagSpoof-App — ohne Hardware.
- `build --pan … --name … --expiry YYMM --service NNN --out card.mag` — erzeugt Track 1 + 2 (ISO/IEC 7811), inkl. LRC-Anzeige.
- `validate card.mag` — prüft Sentinels, Zeichensatz, Feldtrenner, Länge; zeigt LRC.
- `info card.mag` — liest PAN, Name, Expiry, Service-Code aus.

Beispiel:
```
python magtool/magtool.py build --pan 4111111111111111 --name "DOE/JOHN" --expiry 2812 --service 201 --out card.mag
python magtool/magtool.py validate card.mag
python magtool/magtool.py info card.mag
```

### flipperbridge (`flipperbridge/flipperbridge.py`)
Schlanke Flipper-Steuerung über USB-CDC (Pi/PC) — Fundament des Pi-Decks. Nur `pyserial`.
- `info` — device_info als Key/Value.
- `ls <pfad>` · `send <lokal> <remote>` (write_chunk **CR-terminiert** + md5-Verifikation) · `rm` · `launch` · `close` · `raw <cmd>`.
- Live gegen COM3 verifiziert (Upload md5-geprüft). Auf dem Pi: `-p /dev/ttyACM0`.

```
python flipperbridge/flipperbridge.py -p /dev/ttyACM0 info
python flipperbridge/flipperbridge.py -p /dev/ttyACM0 send app.fap /ext/apps/Tools/app.fap
```

### vault-organizer (`vault-organizer/vault_organizer.py`)
Indexiert & entdoppelt Flipper-Captures **lokal** (`.sub/.nfc/.rfid/.ir`). Extrahiert Metadaten (Frequenz/Protokoll, UID/Typ …), findet Inhalts-Duplikate per Hash, schreibt `vault_index.csv` + `vault_index.md`. **Lädt nichts hoch** (sensible Captures bleiben lokal).
```
python vault-organizer/vault_organizer.py <capture-ordner> --out out/
```
An 1373 .sub getestet → 896 einzigartig, 477 Duplikate erkannt.

### cockpit (`cockpit/cockpit.py`)
Pi-Deck-Cockpit auf Basis von flipperbridge:
- `dash` / `status` / `apps` — Momentaufnahme (Geräte-/Radio-/SD-Status + App-Landschaft je Kategorie).
- `live [--interval N] [--count C]` — selbst-aktualisierendes Dashboard (ANSI).
- `pull <flipper-ordner> <dest>` — Text-Captures Flipper→PC ziehen.
- `sync <flipper-ordner> <dest>` — pull **+** vault-organizer-Index in einem Befehl.
- `radio rx <freq> [--seconds N]` — SubGHz-Monitor (read-only) · `radio decode <datei>` · `radio tx <datei>` (autorisiert).
```
python cockpit/cockpit.py -p /dev/ttyACM0 live
python cockpit/cockpit.py -p /dev/ttyACM0 sync /ext/subghz ./caps
```
Alle Befehle live gegen COM3 getestet.

### webdeck (`webdeck/webdeck.py`)
Browser-Dashboard fürs Pi-Deck — **dependency-frei** (Python-Stdlib `http.server` + flipperbridge, kein Flask). G4MEOVER-Look. Endpunkte über die Bridge (serialisiert per Lock):
- **Live-Status** (Gerät/SD/Radio, auto-refresh) + **App-Landschaft** (Balken je Kategorie).
- **SubGHz** rx-Monitor (read-only) / tx from file (autorisiert).
- **Captures-Browser**: „Sync now" zieht Captures vom Flipper, indiziert sie (vault-organizer) und zeigt sie filterbar mit Metadaten (Freq/Protokoll).
- **Report** (`/report`): eigenständiger, druck-/speicherbarer HTML-Report — Zusammenfassung, Typ-Verteilung, Duplikat-Gruppen, Tabelle.
```
python webdeck/webdeck.py -p /dev/ttyACM0 --host 0.0.0.0 --port 8080 --captures ./captures
# dann im LAN: http://<pi-ip>:8080
```
Live getestet: Status, Apps, Radio, Sync+Captures-Index.

## Geplant
- Report-Export (PDF/HTML) aus dem Captures-Index; Cockpit-Captures-DB (persistent).

## Rahmen
Alles defensiv / autorisiert. Keine fremden Kartendaten oder echten Zugangsdaten im Repo.
