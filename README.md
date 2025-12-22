
## Backfill Command

docker compose exec airflow-scheduler \
    airflow backfill create\
    --dag-id weekly_billboard_pipeline \
    --from-date 2000-01-01 \
    --to-date 2025-12-09

## copy backfill Bash script into scheduler:
docker cp backfill_yearly.sh billboard-charts-analysis-airflow-scheduler-1:/opt/airflow/backfill_yearly.sh

## exec into container:

- docker compose exec --user root airflow-scheduler bash


## Run in container:

- chmod +x /opt/airflow/backfill_yearly.sh
- /backfill_yearly.sh

docker compose exec airflow-scheduler bash

airflow tasks state weekly_billboard_pipeline load_weekly_music_data 2000-01-07


airflow dags list-runs weekly_billboard_pipeline


docker compose exec postgres psql -U airflow airflow


\list
\c music_warehouse
\dt
select * from chart_weeks


DELETE FROM dag_run WHERE dag_id='weekly_billboard_pipeline';
DELETE FROM task_instance WHERE dag_id='weekly_billboard_pipeline';
