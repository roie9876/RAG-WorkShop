#!/bin/bash
# Run the strategy evaluation in the background
# Usage: bash run_eval.sh [--quick] [--category NAME]

cd /Users/robenhai/RAG-WorkShop/modules/module-7-pipeline
source backend/venv/bin/activate

echo "Starting evaluation at $(date)"
echo "Logs: /tmp/eval_output.txt"
echo "PID file: /tmp/eval_pid.txt"

python strategy_eval.py "$@" > /tmp/eval_output.txt 2>&1
EXIT_CODE=$?

echo ""
echo "Evaluation finished at $(date) with exit code $EXIT_CODE"
echo "Results: eval_results/eval_results.json"
echo "Report:  eval_results/eval_report.md"
