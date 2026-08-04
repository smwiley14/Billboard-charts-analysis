# Pin the exact Airflow version. NEVER use :latest — Airflow ties its metadata
# schema to the version, so an unpinned rebuild silently desyncs the DB and the
# dag-processor crash-loops with "Database migration required".
FROM apache/airflow:3.3.0

COPY requirements.txt /requirements.txt

RUN pip install --upgrade pip && \
        pip install --no-cache-dir -r /requirements.txt
