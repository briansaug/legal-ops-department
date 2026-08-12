#!/usr/bin/env bash
# Fetch CUAD v1 (Contract Understanding Atticus Dataset).
#
# License: the dataset and annotations are CC BY 4.0 (Atticus Project).
# Atticus makes no representation about the license status of the underlying
# contracts, which are public SEC EDGAR filings. See data/README.md.
#
# ~106 MB download. Everything lands under data/cuad/ and data/contracts/,
# both of which are gitignored.
set -euo pipefail
cd "$(dirname "$0")"

ZIP_URL="https://zenodo.org/records/4595826/files/CUAD_v1.zip?download=1"

mkdir -p cuad
if [ ! -f cuad/CUAD_v1.zip ]; then
  echo "Downloading CUAD v1 (~106 MB)..."
  curl -L -o cuad/CUAD_v1.zip "$ZIP_URL"
fi

echo "Extracting..."
unzip -q -o cuad/CUAD_v1.zip -d cuad

echo "Staging the 12 frozen contracts and verifying the gold set..."
python3 gold/build_gold_set.py

echo "Done. Contracts in data/contracts/, gold labels in data/gold/intake_gold.csv"
