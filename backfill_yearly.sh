DAG_ID="weekly_billboard_pipeline"
START_YEAR=2000
END_YEAR=2025

SERVICE="airflow-scheduler"

for YEAR in $(seq $START_YEAR $END_YEAR); do
    START_DATE="${YEAR}-01-01"
    END_DATE="${YEAR}-12-31"

    echo " Backfilling $DAG_ID for year ${YEAR}"
    echo " From: $START_DATE  To: $END_DATE"

    docker compose exec $SERVICE \
      airflow backfill create \
        --dag-id $DAG_ID \
        --start-date $START_DATE \
        --end-date $END_DATE

    sleep 3
done
