#!/usr/bin/env bash
set -euo pipefail

for directory in /app/coding_runs /app/metric_outputs; do
  mkdir -p "$directory"
  chown benchmark:benchmark "$directory"
done

if (( $# == 0 )); then
  set -- --help
fi

if [[ "$1" == "run-bench" ]]; then
  shift
  exec setpriv --reuid=benchmark --regid=benchmark --init-groups \
    /bin/bash /app/run_bench.sh "$@"
fi

if [[ "$1" == "cal-acc" ]]; then
  shift
  exec setpriv --reuid=benchmark --regid=benchmark --init-groups \
    /bin/bash /app/cal_acc.sh "$@"
fi

exec setpriv --reuid=benchmark --regid=benchmark --init-groups \
  /app/.venv/bin/sidetaskbench "$@"
