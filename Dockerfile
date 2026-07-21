FROM apache/airflow:latest

COPY requirements.txt /requirements.txt

RUN pip install --upgrade pip && \
        pip install --no-cache-dir -r /requirements.txt
