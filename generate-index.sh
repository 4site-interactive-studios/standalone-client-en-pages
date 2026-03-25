#!/bin/bash
# Auto-generates index.html from all mirrored EN pages in the repo.
# Run from repo root: ./generate-index.sh

cd "$(dirname "$0")"

python3 generate-index.py

echo "Generated index.html with $(grep -c 'class="card"' index.html) cards and $(grep -c '<li class="list-org"' index.html) list entries."
