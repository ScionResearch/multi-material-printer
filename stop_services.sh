#!/bin/bash
# stop_services.sh
# Stops the Flask web app and the print manager using stored PIDs if available
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="${ROOT_DIR}/run"

stop_one() {
  local name="$1" pid_file="$2" pattern="$3"
  if [ -f "$pid_file" ]; then
    PID=$(cat "$pid_file" 2>/dev/null || true)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      echo "Stopping $name (PID $PID)"
      kill "$PID" || true
      sleep 1
      if kill -0 "$PID" 2>/dev/null; then
        echo "$name did not exit, sending SIGKILL"
        kill -9 "$PID" 2>/dev/null || true
      fi
      rm -f "$pid_file"
      return
    fi
  fi

  # Fallback search by pattern
  PIDS=$(pgrep -f "$pattern" || true)
  if [ -n "$PIDS" ]; then
    echo "Stopping $name by pattern ($pattern): $PIDS"
    kill $PIDS 2>/dev/null || true
  else
    echo "$name not running"
  fi
}

stop_one "Web App" "${PID_DIR}/web_app.pid" "web-app/app.py"
stop_one "Print Manager" "${PID_DIR}/print_manager.pid" "src/controller/print_manager.py"

echo "Stop sequence complete."