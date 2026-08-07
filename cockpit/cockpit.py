#!/usr/bin/env python3
"""G4MEOVER Pi-Deck Cockpit - Live-Statusansicht des Flipper Zero.

Baut auf flipperbridge auf (USB-CDC). Zeigt Geraet, Speicher, Radio-Status,
laufende App und die installierte App-Landschaft (pro Kategorie).

  cockpit.py -p COM3 status
  cockpit.py -p COM3 apps
  cockpit.py -p COM3 dash     # alles zusammen

Auf dem Pi: -p /dev/ttyACM0
"""
import argparse
import os
import re
import subprocess
import sys
import time

# flipperbridge aus dem Nachbarordner importierbar machen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "flipperbridge"))
from flipperbridge import FlipperBridge  # noqa: E402

APP_ROOT = "/ext/apps"
CATS = ["Sub-GHz", "NFC", "RFID", "Infrared", "GPIO", "iButton",
        "USB", "Bluetooth", "Games", "Media", "Tools", "Scripts"]


def _int(s):
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else 0


def storage_free(fb):
    txt = fb.cmd('storage info "/ext"')
    total = free = 0
    for line in txt.splitlines():
        if "total" in line:
            total = _int(line)
        elif "free" in line:
            free = _int(line)
    return total, free


def count_apps(fb):
    counts = {}
    total = 0
    for cat in CATS:
        out = fb.storage_list(f"{APP_ROOT}/{cat}")
        n = len(re.findall(r"\[F\].+\.fap", out))
        if n:
            counts[cat] = n
            total += n
    return counts, total


def show_status(fb):
    info = fb.device_info()
    total, free = storage_free(fb)
    running = fb.loader_info()
    print("== GERAET ==")
    for k in ("hardware_name", "firmware_version", "firmware_api_major",
              "firmware_api_minor", "firmware_branch", "radio_alive"):
        if k in info:
            print(f"  {k:22}: {info[k]}")
    if total:
        used_pct = 100 * (total - free) / total
        print(f"  {'sd_card_kib':22}: {free} frei / {total} total  ({used_pct:.1f}% belegt)")
    print(f"  {'running_app':22}: {running.strip() or 'Desktop'}")


def show_apps(fb):
    counts, total = count_apps(fb)
    print(f"== INSTALLIERTE APPS ({total}) ==")
    width = max((len(c) for c in counts), default=6)
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "#" * min(n, 40)
        print(f"  {cat:<{width}} {n:4d}  {bar}")


CAPTURE_EXTS = (".sub", ".nfc", ".rfid", ".ir")


def pull_captures(fb, src, dest, max_size, limit):
    """Laedt Text-Captures rekursiv Flipper->PC (fuer den vault-organizer-Index)."""
    n = skipped = 0
    for full, size in fb.storage_walk(src):
        if not full.lower().endswith(CAPTURE_EXTS):
            continue
        if size > max_size:
            skipped += 1
            continue
        rel = full[len(src):].lstrip("/")
        local = os.path.join(dest, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
        with open(local, "w", encoding="utf-8", newline="\n") as f:
            f.write(fb.storage_read(full))
        n += 1
        print(f"  [{n}] {rel} ({size}b)")
        if limit and n >= limit:
            break
    print(f"\nGezogen: {n} | uebersprungen (>{max_size}b): {skipped}")
    print(f"-> vault-organizer laufen lassen: python ../vault-organizer/vault_organizer.py {dest}")
    return n


def live_monitor(fb, interval, count):
    """Selbst-aktualisierendes Dashboard (ANSI). count=0 -> endlos (Ctrl-C)."""
    counts, app_total = count_apps(fb)  # einmalig (teuer)
    i = 0
    try:
        while count == 0 or i < count:
            info = fb.device_info()
            total, free = storage_free(fb)
            running = fb.loader_info().strip() or "Desktop"
            sys.stdout.write("\033[2J\033[H")  # clear + home
            print("G4MEOVER PI-DECK - LIVE")
            print("=" * 40)
            print(f"  {info.get('hardware_name','?')}  |  {info.get('firmware_version','?')}  "
                  f"|  API {info.get('firmware_api_major','?')}.{info.get('firmware_api_minor','?')}")
            print(f"  Radio : {info.get('radio_alive','?')}")
            if total:
                print(f"  SD    : {100*(total-free)/total:.1f}% belegt ({free} KiB frei)")
            print(f"  App   : {running}")
            print(f"  Apps  : {app_total} installiert  (GPIO {counts.get('GPIO',0)}, "
                  f"Tools {counts.get('Tools',0)}, Sub-GHz {counts.get('Sub-GHz',0)})")
            print(f"\n  Refresh {interval}s | Ctrl-C beendet")
            sys.stdout.flush()
            i += 1
            if count and i >= count:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nbeendet.")


def main():
    ap = argparse.ArgumentParser(description="G4MEOVER Pi-Deck Cockpit")
    ap.add_argument("-p", "--port", required=True)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status")
    sub.add_parser("apps")
    sub.add_parser("dash")
    lv = sub.add_parser("live", help="selbst-aktualisierendes Dashboard")
    lv.add_argument("--interval", type=int, default=5)
    lv.add_argument("--count", type=int, default=0, help="Anzahl Refreshes (0=endlos)")
    sp = sub.add_parser("pull", help="Text-Captures Flipper->PC ziehen")
    sp.add_argument("src", help="Flipper-Ordner, z.B. /ext/subghz")
    sp.add_argument("dest", help="lokales Zielverzeichnis")
    sp.add_argument("--max-size", type=int, default=16384, help="max. Dateigroesse (Bytes)")
    sp.add_argument("--limit", type=int, default=0, help="max. Anzahl (0=alle)")

    rp = sub.add_parser("radio", help="SubGHz ueber die Flipper-CLI")
    rsub = rp.add_subparsers(dest="rcmd", required=True)
    r_rx = rsub.add_parser("rx", help="Monitor (read-only)")
    r_rx.add_argument("freq", type=int, help="Frequenz in Hz, z.B. 433920000")
    r_rx.add_argument("--seconds", type=int, default=8)
    r_rx.add_argument("--device", type=int, default=0, help="0=intern, 1=extern CC1101")
    r_dec = rsub.add_parser("decode", help="RAW-.sub analysieren (read-only)")
    r_dec.add_argument("file", help="Flipper-Pfad einer RAW .sub")
    r_tx = rsub.add_parser("tx", help="von .sub senden (autorisiert!)")
    r_tx.add_argument("file", help="Flipper-Pfad einer .sub")
    r_tx.add_argument("--repeat", type=int, default=1)
    r_tx.add_argument("--device", type=int, default=0)

    sy = sub.add_parser("sync", help="pull + Index in einem")
    sy.add_argument("src", help="Flipper-Ordner, z.B. /ext/subghz")
    sy.add_argument("dest", help="lokales Zielverzeichnis")
    sy.add_argument("--max-size", type=int, default=16384)
    sy.add_argument("--limit", type=int, default=0)

    args = ap.parse_args()
    cmd = args.cmd or "dash"

    with FlipperBridge(args.port) as fb:
        if cmd == "pull":
            print(f"PULL {args.src} -> {args.dest}")
            pull_captures(fb, args.src.rstrip("/"), args.dest, args.max_size, args.limit)
            return
        if cmd == "live":
            live_monitor(fb, args.interval, args.count)
            return
        if cmd == "sync":
            idx = os.path.join(args.dest, "_idx")
            print(f"SYNC {args.src} -> {args.dest}  (+ Index)")
            n = pull_captures(fb, args.src.rstrip("/"), args.dest, args.max_size, args.limit)
            if n:
                organizer = os.path.join(os.path.dirname(__file__), "..", "vault-organizer", "vault_organizer.py")
                print("\n-- Index --")
                subprocess.run([sys.executable, organizer, args.dest, "--out", idx], check=False)
            return
        if cmd == "radio":
            if args.rcmd == "rx":
                print(f"RX-Monitor {args.freq} Hz, {args.seconds}s (dev {args.device}) ...")
                print(fb.stream(f"subghz rx {args.freq} {args.device}", args.seconds).strip())
            elif args.rcmd == "decode":
                print(fb.cmd(f'subghz decode_raw "{args.file}"', 12))
            elif args.rcmd == "tx":
                print(f"TX von {args.file} x{args.repeat} (autorisiert) ...")
                print(fb.cmd(f'subghz tx_from_file "{args.file}" {args.repeat} {args.device}', 15))
            return
        print("G4MEOVER PI-DECK COCKPIT")
        print("=" * 40)
        if cmd in ("status", "dash"):
            show_status(fb)
        if cmd in ("apps", "dash"):
            print()
            show_apps(fb)


if __name__ == "__main__":
    main()
