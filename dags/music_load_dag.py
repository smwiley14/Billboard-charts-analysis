from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

from src.load import load_to_postgres

default_args = {
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "weekly_music_pipeline",
    default_args=default_args,
    schedule="0 12 * * FRI",
    start_date=datetime(2010, 1, 1),   
    catchup=True,                      
) as dag:
    load = PythonOperator(
        task_id="load_music_data",
        python_callable=load_to_postgres,
        op_kwargs={"date": "{{ ds }}"},
    )
