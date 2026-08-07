#!/usr/bin/env python3
"""G4MEOVER Vault-Organizer - indexiert & entdoppelt Flipper-Captures lokal.

Scannt einen Ordner nach .sub/.nfc/.rfid/.ir, extrahiert Metadaten, findet Duplikate
per Inhalts-Hash und schreibt einen Index (CSV) + eine Markdown-Uebersicht.

REIN LOKAL - lädt nichts hoch. Sensible Captures (z.B. B1.sub..B9.sub) bleiben, wo sie sind.

Aufruf:
  vault_organizer.py <root-ordner> [--out <ausgabe-verzeichnis>]
"""
import argparse
import csv
import hashlib
import os
import re
from collections import Counter, defaultdict

EXTS = (".sub", ".nfc", ".rfid", ".ir")


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def kv(text, key):
    m = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def content_hash(text):
    """Hash ueber inhaltliche Zeilen (Kommentare/Whitespace normalisiert)."""
    lines = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith("Filetype") or ln.startswith("Version"):
            continue
        lines.append(ln)
    return hashlib.sha1("\n".join(lines).encode("utf-8", "replace")).hexdigest()


def parse_meta(path, text):
    ext = os.path.splitext(path)[1].lower()
    meta = {"type": ext[1:], "detail": ""}
    if ext == ".sub":
        freq = kv(text, "Frequency")
        proto = kv(text, "Protocol") or kv(text, "Preset")
        meta["detail"] = f"{freq}Hz {proto}".strip()
    elif ext == ".nfc":
        dtype = kv(text, "Device type")
        uid = kv(text, "UID")
        meta["detail"] = f"{dtype} UID:{uid}".strip()
    elif ext == ".rfid":
        kt = kv(text, "Key type")
        data = kv(text, "Data")
        meta["detail"] = f"{kt} {data}".strip()
    elif ext == ".ir":
        # erste Protokoll-/Namenszeile
        name = kv(text, "name")
        proto = kv(text, "protocol")
        meta["detail"] = f"{name} {proto}".strip()
    return meta


def scan(root):
    rows = []
    by_hash = defaultdict(list)
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith(EXTS):
                continue
            p = os.path.join(dirpath, fn)
            text = read_text(p)
            h = content_hash(text)
            meta = parse_meta(p, text)
            rel = os.path.relpath(p, root)
            rows.append({
                "file": rel, "type": meta["type"], "detail": meta["detail"],
                "hash": h, "size": os.path.getsize(p),
            })
            by_hash[h].append(rel)
    return rows, by_hash


def main():
    ap = argparse.ArgumentParser(description="G4MEOVER Vault-Organizer")
    ap.add_argument("root", help="Wurzelordner mit Captures")
    ap.add_argument("--out", default=".", help="Ausgabeverzeichnis")
    args = ap.parse_args()

    rows, by_hash = scan(args.root)
    dupes = {h: fs for h, fs in by_hash.items() if len(fs) > 1}
    type_counts = Counter(r["type"] for r in rows)
    unique = len(by_hash)
    dup_files = sum(len(fs) - 1 for fs in dupes.values())

    os.makedirs(args.out, exist_ok=True)
    csv_path = os.path.join(args.out, "vault_index.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "type", "detail", "hash", "size"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["type"], r["file"])))

    md_path = os.path.join(args.out, "vault_index.md")
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Vault-Index\n\n")
        f.write(f"Gescannt: `{args.root}`\n\n")
        f.write(f"- Dateien gesamt : **{len(rows)}**\n")
        f.write(f"- Einzigartig    : **{unique}**\n")
        f.write(f"- Duplikate      : **{dup_files}** (redundante Kopien)\n\n")
        f.write("## Nach Typ\n\n")
        for t, n in type_counts.most_common():
            f.write(f"- `.{t}`: {n}\n")
        if dupes:
            f.write("\n## Duplikat-Gruppen (gleicher Inhalt)\n\n")
            for h, fs in sorted(dupes.items(), key=lambda x: -len(x[1])):
                f.write(f"- `{h[:10]}` ({len(fs)}x): {', '.join(fs)}\n")

    print(f"Dateien: {len(rows)} | einzigartig: {unique} | Duplikate: {dup_files}")
    for t, n in type_counts.most_common():
        print(f"  .{t}: {n}")
    print(f"\nIndex  -> {csv_path}")
    print(f"Report -> {md_path}")


if __name__ == "__main__":
    main()
