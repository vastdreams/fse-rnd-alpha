#!/bin/bash
# PATH: scripts/run_all_ingesters.sh
# PURPOSE: Run data ingestion scripts concurrently on EC2

echo "Starting concurrent data ingestion..."

# Fama-French Factors
python3 scripts/ingest_ff_factors.py &
PID1=$!

# Risk-Free Rates
python3 scripts/ingest_risk_free_rates.py &
PID2=$!

# S&P 500 Historical Constituents
python3 scripts/ingest_sp500_historical.py &
PID3=$!

# Wait for constituents before running delisting returns
wait $PID3
echo "Historical constituents complete. Starting delisting returns..."

# Delisting Returns
python3 scripts/ingest_delisting_returns.py &
PID4=$!

# Wait for all remaining
wait $PID1 $PID2 $PID4

echo "All data ingestion complete."

