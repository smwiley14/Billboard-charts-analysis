#!/bin/bash
# Script to run the Streamlit dashboard

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create one with MUSIC_WAREHOUSE_DATABASE_URL set."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if MUSIC_WAREHOUSE_DATABASE_URL is set
if [ -z "$MUSIC_WAREHOUSE_DATABASE_URL" ]; then
    echo "Error: MUSIC_WAREHOUSE_DATABASE_URL not set in .env file"
    exit 1
fi

# Run Streamlit
streamlit run dashboard.py --server.port 8501


