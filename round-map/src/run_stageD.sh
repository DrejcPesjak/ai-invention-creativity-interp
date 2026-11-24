#!/bin/bash
# Stage D driver: one model per process, level by level. Stops when the open list is empty.
cd "$(dirname "$0")/.."
PY=/home/drew99/venvs/ml/bin/python
for L in 0 1 2 3; do
  if [ $L -gt 0 ]; then
    n=$($PY -c "import json;print(len(json.load(open('results/D/open_$L.json'))))")
    [ "$n" = "0" ] && { echo "level $L: nothing open, done"; break; }
  fi
  [ -f results/D/pass1_$L.json ] || $PY src/stageD.py pass1 $L || exit 1
  [ -f results/D/pass2_$L.json ] || $PY src/stageD.py pass2 $L || exit 1
  [ -f results/D/open_$((L+1)).json ] || $PY src/stageD.py pass3 $L || exit 1
done
