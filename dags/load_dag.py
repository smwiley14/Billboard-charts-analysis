from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from src.load import load_to_postgres

default_args = {
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=15),  # Kill task if it runs longer than 15 min
}

with DAG(
    "weekly_billboard_pipeline",
    default_args=default_args,
    schedule="0 12 * * FRI",
    start_date=datetime(1999, 12, 30),   
    catchup=True,      
    max_active_runs=1
    # concurrency=4,                
) as dag:
    load = PythonOperator(
        task_id="load_weekly_music_data",
        python_callable=load_to_postgres,
        op_kwargs={"date": "{{ ds }}"},
    )
