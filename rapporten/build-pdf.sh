#!/usr/bin/env bash
# Rendert het strategisch marktrapport naar PDF met headless Chromium.
#
#   ./rapporten/build-pdf.sh
#
# Het HTML-bestand is een fragment (bedoeld voor de Artifact-wrapper), dus het
# wordt hier eerst in een volledig document gehesen met een @page-regel erbij.

set -euo pipefail
cd "$(dirname "$0")/.."

SRC="rapporten/hairstuff-strategisch-marktrapport-2026-08.html"
OUT="rapporten/Hairstuff-Strategisch-Marktrapport-2026-08.pdf"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
[ -x "$CHROME" ] || CHROME="$(command -v chromium || command -v chromium-browser || command -v google-chrome)"
[ -x "$CHROME" ] || { echo "Geen Chromium gevonden. Zet CHROME= naar het pad."; exit 1; }

python3 - "$SRC" "$TMP/print.html" <<'PY'
import sys
src = open(sys.argv[1], encoding='utf-8').read()
extra = """
<style>
@page { size: A4; margin: 15mm 14mm 15mm 14mm; }
html, body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-size: 10pt; }
@media print {
  .call, .verdict > div, .stats .stat, thead th, .chip { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  section#sdata, section#s1, section#s2, section#s3, section#s4, section#s5,
  section#s6, section#s7, section#s8, section#s9, section#s10, section#s11,
  section#s12, section#s13, section#bron { break-before: page; page-break-before: always; }
  h2, h3 { break-after: avoid; page-break-after: avoid; }
  tr, .call, .verdict, .stats { break-inside: avoid; page-break-inside: avoid; }
  table { width: 100%; }
  .masthead { padding-top: 0; }
}
</style>
"""
head, body = src.split('</style>', 1)
open(sys.argv[2], 'w', encoding='utf-8').write(
    '<!doctype html>\n<html lang="nl">\n<head>\n<meta charset="utf-8">\n'
    + head + '</style>\n' + extra + '\n</head>\n<body>\n' + body + '\n</body>\n</html>\n')
PY

"$CHROME" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --virtual-time-budget=20000 --run-all-compositor-stages-before-draw \
  --print-to-pdf="$OUT" "file://$TMP/print.html" 2>/dev/null

python3 - "$OUT" <<'PY'
import sys
from pypdf import PdfReader
r = PdfReader(sys.argv[1])
pages = [p.extract_text() or '' for p in r.pages]
blank = [i + 1 for i, t in enumerate(pages) if len(t.strip()) < 40]
print(f"{sys.argv[1]}: {len(r.pages)} pagina's, {sum(len(t) for t in pages):,} tekens"
      + (f", LEGE PAGINA'S: {blank}" if blank else ", geen lege pagina's"))
PY
