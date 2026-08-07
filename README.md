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
- `dash` / `status` / `apps` — Live-Dashboard (Geräte-/Radio-/SD-Status + App-Landschaft je Kategorie).
- `pull <flipper-ordner> <dest>` — Text-Captures Flipper→PC ziehen (für den vault-organizer-Index).
- `radio rx <freq> [--seconds N]` — SubGHz-Monitor (read-only) · `radio decode <datei>` — RAW analysieren · `radio tx <datei>` — von .sub senden (autorisiert).
```
python cockpit/cockpit.py -p /dev/ttyACM0 dash
python cockpit/cockpit.py -p /dev/ttyACM0 radio rx 433920000 --seconds 8
```
Live gegen COM3 getestet (Dashboard, Pull+Index, RX-Monitor).

## Geplant
- Cockpit-UI-Politur (TUI), Captures-DB, Report-Generator.

## Rahmen
Alles defensiv / autorisiert. Keine fremden Kartendaten oder echten Zugangsdaten im Repo.
