from src.transform import get_dataframes
import os
from sqlalchemy import create_engine, text
import sqlalchemy as sa
from sqlalchemy import MetaData, Table

output_dir = "data_exports"
os.makedirs(output_dir, exist_ok=True)

database_url = os.getenv("DATABASE_URL")
print(database_url)



from sqlalchemy.dialects.postgresql import insert

def make_upsert(metadata):
    def upsert(table, conn, keys, data_iter):
        sa_table = metadata.tables[table.name]

        rows = [dict(zip(keys, row)) for row in data_iter]

        stmt = insert(sa_table).values(rows)

        pk_cols = [col.name for col in sa_table.primary_key.columns]

        stmt = stmt.on_conflict_do_nothing(
            index_elements=pk_cols
        )

        conn.execute(stmt)
    return upsert

##Notes:
# Pandas version: 2.1.4
# SQLAlchemy version: 1.4.54
## Airflow requires SQLAlchemy 1.4.x, so we need to use the older version.
## Pandas 3.* is not compatible with SQLAlchemy 1.4.x, so we need to use the older version.
def load_to_postgres(date: str):
    """
    Load a single Billboard chart week into Postgres and CSV files.

    `date` should be a YYYY-MM-DD string; this will be used as the `chart_week`
    primary key value in the warehouse schema.
    """
    dfs = get_dataframes(date)
    # for name, df in dfs:
    #     df.to_csv(os.path.join(output_dir, f"{df.name}.csv"), index=False)
        # df.to_sql(name, con=engine, if_exists="append", index=False, method="multi")
        # print(f"  Successfully loaded {len(df)} rows into {name}")

    database_url = os.getenv("MUSIC_WAREHOUSE_DATABASE_URL")
    if database_url:
        # Mask password in debug output
        masked_url = database_url
        if "@" in masked_url:
            parts = masked_url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split(":")
                if len(user_pass) >= 2:
                    masked_url = f"{user_pass[0]}:****@{parts[1]}"
        print(f"DEBUG: DATABASE_URL value: {masked_url}")
    
    # Validate that DATABASE_URL is set and not using placeholder
    if not database_url or database_url == "postgresql://user:pass@host/db":
        raise ValueError(
            "DATABASE_URL environment variable is not set or is using placeholder value.\n"
            "Please set DATABASE_URL to a valid PostgreSQL connection string, e.g.:\n"
            "  postgresql+psycopg2://username:password@hostname:5432/database\n"
            "or\n"
            "  postgresql://username:password@hostname:5432/database\n"
            "\n"
            "If using docker-compose, make sure you've:\n"
            "  1. Added DATABASE_URL to the environment section in docker-compose.yaml\n"
            "  2. Restarted the services: docker-compose restart"
        )
    
    # Create SQLAlchemy engine - pandas requires this for PostgreSQL
    # Ensure the URL uses postgresql+psycopg2:// format for proper driver detection
    if not database_url.startswith("postgresql"):
        raise ValueError(f"Invalid database URL format. Expected postgresql:// or postgresql+psycopg2://, got: {database_url[:20]}...")
    
    # Ensure we're using psycopg2 driver
    if "+psycopg2" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
    
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        echo=False
    )
    metadata = MetaData()
    metadata.reflect(bind=engine)

    upsert_fn = make_upsert(metadata)


    tables = {
        "songs": Table("songs", metadata, autoload_with=engine),
        "artists": Table("artists", metadata, autoload_with=engine),
        "chart_weeks": Table("chart_weeks", metadata, autoload_with=engine),
        "song_artists": Table("song_artists", metadata, autoload_with=engine),
        "chart_entries": Table("chart_entries", metadata, autoload_with=engine),
    }

    print("TYPE OF ENGINE:", type(engine))
    print("ENGINE DIR:", dir(engine))
    print("IS SQLALCHEMY ENGINE:", isinstance(engine, sa.engine.Engine))

    
    # Test connection
    try:
        with engine.connect() as test_conn:
            result = test_conn.execute(text("SELECT 1"))
            result.fetchone()
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection test failed: {e}")
        raise

    # Load dimension / lookup tables first, then junction table, then fact table
    load_order = ["chart_weeks", "songs", "artists", "song_artists", "chart_entries"]

    for name in load_order:
        df = dfs.get(name)
        if df is None or df.empty:
            print(f"Skipping {name}: dataframe is empty or None")
            continue

        print(f"Loading {name} ({len(df)} rows)...")
        
        # Use SQLAlchemy engine - this ensures pandas recognizes it as PostgreSQL
        try:
            if name in ["songs", "artists", "song_artists", "chart_weeks"]:
                df.to_sql(
                    name,
                    engine,
                    if_exists="append",
                    index=False,
                    method=upsert_fn
                )

            elif name == "chart_entries":
                df.to_sql(
                    name,
                    engine,
                    if_exists="append",
                    index=False,
                    method="multi"   # no upsert needed; PK is week+rank
                )
        except Exception as e:
            print(f"  Error loading {name}: {e}")
            raise  # Re-raise to see the full error

        # also write out a CSV export for inspection
        csv_path = os.path.join(output_dir, f"{name}.csv")
        df.to_csv(csv_path, index=False)
        print(f"  Exported CSV to {csv_path}")

