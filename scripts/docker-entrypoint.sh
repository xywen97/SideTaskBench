#!/usr/bin/env bash
set -euo pipefail

for directory in /app/coding_runs /app/metric_outputs; do
  mkdir -p "$directory"
  chown benchmark:benchmark "$directory"
done

if (( $# == 0 )); then
  set -- --help
fi

exec setpriv --reuid=benchmark --regid=benchmark --init-groups \
  /app/.venv/bin/sidetaskbench "$@"
