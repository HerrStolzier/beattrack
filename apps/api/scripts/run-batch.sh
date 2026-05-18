#!/bin/bash
# run-batch.sh — Wrapper for long-running batch jobs in the beattrack API
# Usage:
#   ./scripts/run-batch.sh extract_mert_batch.py --apply --workers 6
#   ./scripts/run-batch.sh backfill_genre.py --apply
#   ./scripts/run-batch.sh --status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="${BEATTRACK_API_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PYTHON="$API_DIR/.venv/bin/python"
LOG_DIR="/private/tmp"

# --------------------------------------------------------------------------- #
# --status: show running batch jobs and tail their logs
# --------------------------------------------------------------------------- #
if [[ "${1:-}" == "--status" ]]; then
  echo "=== Beattrack Batch Status ==="
  echo ""

  found=0
  for pid_file in "$LOG_DIR"/beattrack_*.pid; do
    [[ -e "$pid_file" ]] || continue
    found=1

    pid=$(cat "$pid_file")
    job_name=$(basename "$pid_file" .pid | sed 's/^beattrack_//')
    log_file="$LOG_DIR/${job_name}.log"
    done_file="$LOG_DIR/${job_name}.done"

    if [[ -f "$done_file" ]]; then
      echo "[DONE]    $job_name (PID was $pid)"
    elif kill -0 "$pid" 2>/dev/null; then
      echo "[RUNNING] $job_name (PID $pid)"
      echo "--- last 10 lines of $log_file ---"
      if [[ -f "$log_file" ]]; then
        tail -n 10 "$log_file"
      else
        echo "(no log yet)"
      fi
      echo ""
    else
      echo "[DEAD]    $job_name (PID $pid exited unexpectedly — check $log_file)"
    fi
  done

  if [[ $found -eq 0 ]]; then
    echo "No batch jobs tracked in $LOG_DIR."
  fi
  exit 0
fi

# --------------------------------------------------------------------------- #
# Validate arguments
# --------------------------------------------------------------------------- #
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <script.py> [args...]"
  echo "       $0 --status"
  exit 1
fi

SCRIPT_NAME="$1"
shift  # remaining args are passed to the Python script

SCRIPT_PATH="$API_DIR/scripts/$SCRIPT_NAME"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "Error: Script not found: $SCRIPT_PATH"
  exit 1
fi

if [[ ! -f "$PYTHON" ]]; then
  echo "Error: Python venv not found at $PYTHON"
  exit 1
fi

# Derive a safe job name (strip .py, replace dots/slashes with _)
JOB_NAME=$(basename "$SCRIPT_NAME" .py | tr '/.\ ' '_')
LOG_FILE="$LOG_DIR/${JOB_NAME}.log"
DONE_FILE="$LOG_DIR/${JOB_NAME}.done"
PID_FILE="$LOG_DIR/beattrack_${JOB_NAME}.pid"

# Remove stale .done marker from a previous run
rm -f "$DONE_FILE"

# --------------------------------------------------------------------------- #
# Launch in background
# --------------------------------------------------------------------------- #
(
  cd "$API_DIR"

  echo "=== Beattrack batch job: $SCRIPT_NAME ===" > "$LOG_FILE"
  echo "=== Started: $(date) ===" >> "$LOG_FILE"
  echo "=== Args: $* ===" >> "$LOG_FILE"
  echo "" >> "$LOG_FILE"

  set +e  # we handle the exit code ourselves inside the subshell
  "$PYTHON" "$SCRIPT_PATH" "$@" >> "$LOG_FILE" 2>&1
  EXIT_CODE=$?
  set -e

  echo "" >> "$LOG_FILE"
  echo "=== Finished: $(date) — exit code $EXIT_CODE ===" >> "$LOG_FILE"

  if [[ $EXIT_CODE -eq 0 ]]; then
    touch "$DONE_FILE"
    osascript -e "display notification \"$SCRIPT_NAME finished successfully.\" with title \"Beattrack\"" 2>/dev/null || true
  else
    osascript -e "display notification \"$SCRIPT_NAME FAILED (exit $EXIT_CODE). Check $LOG_FILE\" with title \"Beattrack\"" 2>/dev/null || true
  fi

  rm -f "$PID_FILE"
) &

BG_PID=$!
echo "$BG_PID" > "$PID_FILE"

echo "Started $SCRIPT_NAME in background."
echo "  PID:     $BG_PID"
echo "  Log:     $LOG_FILE"
echo "  Status:  ./scripts/run-batch.sh --status"
