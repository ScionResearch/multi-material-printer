#!/bin/bash
# start_services.sh
# Starts the Flask web app and the print manager in the background with PID & log management
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="${ROOT_DIR}/run"
mkdir -p "${PID_DIR}"

WEB_LOG="${ROOT_DIR}/web_app.log"          # keep existing underscore style already present on device
PM_LOG="${ROOT_DIR}/print_manager.log"

activate_venv() {
	if [ -f "${ROOT_DIR}/venv/bin/activate" ]; then
		# shellcheck disable=SC1090
		source "${ROOT_DIR}/venv/bin/activate"
	fi
}

already_running() {
	local name="$1" pattern="$2"
	if pgrep -f "$pattern" >/dev/null 2>&1; then
		echo "$name appears to already be running (pattern: $pattern). Skipping start." >&2
		return 0
	fi
	return 1
}

activate_venv

echo "Starting services from ${ROOT_DIR}" | tee -a "$WEB_LOG" "$PM_LOG"

# Start web app if not running
if ! already_running "Web App" "web-app/app.py"; then
	(
		cd "${ROOT_DIR}/web-app"
		nohup python3 -u app.py >>"$WEB_LOG" 2>&1 &
		WEB_PID=$!
		echo "$WEB_PID" > "${PID_DIR}/web_app.pid"
		echo "Web app started PID=$WEB_PID (log: $WEB_LOG)"
	)
	echo "Waiting 5 seconds for web app to initialize..."
	sleep 5
fi

# Start print manager if not running
if ! already_running "Print Manager" "src/controller/print_manager.py"; then
	(
		cd "${ROOT_DIR}/src/controller"
		nohup python3 -u print_manager.py >>"$PM_LOG" 2>&1 &
		PM_PID=$!
		echo "$PM_PID" > "${PID_DIR}/print_manager.pid"
		echo "Print manager started PID=$PM_PID (log: $PM_LOG)"
	)
fi

echo "Both services ensured running. Access the web UI at: http://$(hostname -I | awk '{print $1}'):5000" | tee -a "$WEB_LOG"
echo "Use ./stop_services.sh to stop them." 