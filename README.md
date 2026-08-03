# 🎵 Billboard Hot 100 — Data Pipeline & Dashboard

**A quarter-century of the Billboard Hot 100, scraped weekly, enriched with music metadata, and turned into an interactive dashboard.**

This project runs an [Apache Airflow](https://airflow.apache.org/) pipeline that pulls the [Billboard Hot 100](https://www.billboard.com/charts/hot-100/) chart every week from 2000 to today, enriches each song with data from the Spotify, MusicBrainz, and ReccoBeats APIs, and loads it all into a normalized PostgreSQL warehouse. A Streamlit + Plotly dashboard sits on top for exploring trends across 25 years of pop music.

[![Live Dashboard](https://img.shields.io/badge/Live_Dashboard-billboard.samwiley--stuff.com-1DB954?style=for-the-badge)](https://billboard.samwiley-stuff.com)

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Apache Airflow](https://img.shields.io/badge/Apache_Airflow-017CEE?style=flat&logo=apacheairflow&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?style=flat&logo=pandas&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat&logo=plotly&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

<img width="855" alt="Billboard dashboard — trends view" src="https://github.com/user-attachments/assets/291c7f7f-a72b-4359-a8c9-b9624f13ef5a" />

<img width="564" alt="Billboard dashboard — detail view" src="https://github.com/user-attachments/assets/20fab4d6-56de-4d9a-af54-83d82a40c9ff" />

---

## Architecture

An Airflow DAG orchestrates a weekly Extract → Enrich → Transform → Load pipeline. Each song from the chart is matched against several music APIs, normalized, and upserted into the warehouse; the dashboard reads directly from Postgres.

```mermaid
flowchart LR
    BB["Billboard Hot 100<br/>(weekly scrape)"] --> EX["Extract"]
    EX --> EN["Enrich<br/>Spotify · MusicBrainz · ReccoBeats"]
    EN --> TR["Transform<br/>(normalize songs / artists)"]
    TR --> LD["Load<br/>(idempotent upsert)"]
    LD --> DB[("music_warehouse<br/>PostgreSQL")]
    DB --> DASH["Streamlit + Plotly<br/>dashboard"]
    AF["Apache Airflow"] -.orchestrates.-> EX
```

## The pipeline

- **Schedule** — the `weekly_billboard_pipeline` DAG runs every Friday (`0 12 * * FRI`) with a `start_date` in 1999 and `catchup=True`, so a first run **backfills every week back to 2000** (≈1,300 charts). A helper, `backfill_yearly.sh`, runs the backfill a year at a time to keep it manageable.
- **Extract** — scrapes the Hot 100 with [`billboard.py`](https://pypi.org/project/billboard.py/) and pulls track/artist metadata and audio features from **Spotify** (`spotipy`), **MusicBrainz** (`musicbrainzngs`), and **ReccoBeats**. A Spotify cache (`src/build_spotify_cache.py`) cuts down on repeat API calls.
- **Transform** — resolves songs and artists across sources, normalizes artist names, and builds a relational model (songs, artists, and a song↔artist join).
- **Load** — writes to Postgres with SQLAlchemy using `INSERT ... ON CONFLICT DO NOTHING`, so re-running any week is **idempotent** and safe.

## Features

- 📈 **25+ years of weekly chart data** in one queryable warehouse.
- 🔀 **Multi-source enrichment** — Spotify, MusicBrainz, and ReccoBeats combined to fill in track metadata and audio features.
- ⏳ **Backfill + incremental** — one DAG both backfills history and keeps current via the weekly schedule.
- ♻️ **Idempotent loads** — upserts mean no duplicates on retries or re-runs.
- 📊 **Interactive dashboard** — a Streamlit + Plotly app for exploring artists, songs, and audio-feature trends over time.
- 🐳 **Fully Dockerized** — the whole Airflow stack, Postgres, and the dashboard run under Docker Compose.

## Tech stack

| Layer | Technologies |
| --- | --- |
| **Orchestration** | Apache Airflow |
| **Ingestion** | Python, `billboard.py`, `spotipy`, `musicbrainzngs`, ReccoBeats, requests |
| **Processing** | pandas, SQLAlchemy, psycopg2 |
| **Storage** | PostgreSQL |
| **Dashboard** | Streamlit, Plotly |
| **Infra** | Docker Compose |

## Getting started

### Prerequisites
- Docker & Docker Compose
- Spotify API credentials (a free [developer app](https://developer.spotify.com/dashboard) → client ID & secret)

### Configure

Create a `.env` file with your credentials and database URLs:

```bash
# Spotify (Extract)
CLIENT_ID=your_spotify_client_id
CLIENT_SECRET=your_spotify_client_secret
REDIRECT_URI=http://localhost:8888/callback

# Warehouse
DATABASE_URL=postgresql://airflow:airflow@postgres:5432/music_warehouse
MUSIC_WAREHOUSE_DATABASE_URL=postgresql://airflow:airflow@postgres:5432/music_warehouse
```

> A pre-built snapshot of the warehouse is included as `music_warehouse.sql` if you'd rather explore the data than run the full backfill.

### Run

```bash
git clone https://github.com/smwiley14/Billboard-charts-analysis.git
cd Billboard-charts-analysis

docker compose up --build
```

- **Airflow UI** → http://localhost:8080 — unpause `weekly_billboard_pipeline` to start ingesting (it will begin backfilling).
- **Dashboard** → http://localhost:8501

To run just the dashboard against an existing warehouse:

```bash
./run_dashboard.sh        # or: docker build -f Dockerfile.dashboard -t billboard-dashboard .
```

Deployment guides (systemd, Docker, Nginx reverse proxy, HTTPS) live in [`deploy/`](deploy/).

## Project structure

```
.
├── dags/
│   └── load_dag.py          # weekly_billboard_pipeline DAG
├── src/
│   ├── extract.py           # Billboard scrape + Spotify/MusicBrainz/ReccoBeats clients
│   ├── transform.py         # normalize songs & artists
│   ├── load.py              # idempotent upsert into Postgres
│   └── build_spotify_cache.py
├── dashboard.py             # Streamlit + Plotly dashboard
├── music_warehouse.sql      # warehouse snapshot
├── backfill_yearly.sh       # year-by-year backfill helper
├── deploy/                  # deployment guides
├── docker-compose.yaml      # Airflow + Postgres + dashboard
└── Dockerfile.dashboard     # standalone dashboard image
```

## Data sources

Chart data from [Billboard](https://www.billboard.com/charts/hot-100/); track and artist metadata from [Spotify](https://developer.spotify.com/), [MusicBrainz](https://musicbrainz.org/), and [ReccoBeats](https://reccobeats.com/). Used here for a non-commercial, educational project.

---

Built by [Sam Wiley](https://github.com/smwiley14) · [Live dashboard](https://billboard.samwiley-stuff.com)
