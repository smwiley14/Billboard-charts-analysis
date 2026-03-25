import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Billboard Charts Analysis",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1DB954;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1DB954;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_engine():
    """Create and cache database engine connection."""
    database_url = os.getenv("MUSIC_WAREHOUSE_DATABASE_URL")
    if not database_url:
        st.error("MUSIC_WAREHOUSE_DATABASE_URL environment variable not set")
        return None
    
    # Ensure we're using psycopg2 driver
    if not database_url.startswith("postgresql"):
        st.error(f"Invalid database URL format. Expected postgresql://")
        return None
    
    if "+psycopg2" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            echo=False
        )
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_data(query, params=None):
    """Load data from database with caching."""
    engine = get_db_engine()
    if not engine:
        return None
    
    try:
        with engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            return df
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return None

def escape_sql_string(value):
    """Escape single quotes in SQL string values."""
    return str(value).replace("'", "''")

@st.cache_data(ttl=3600)
def get_chart_week_bounds():
    """Get min/max chart weeks for global date filters."""
    bounds_query = """
    SELECT 
        MIN(chart_week) AS min_week,
        MAX(chart_week) AS max_week
    FROM chart_entries
    WHERE chart_week IS NOT NULL
    """
    return load_data(bounds_query)

def build_chart_week_filter(filters, alias="ce"):
    """Build reusable chart week SQL filter and parameters."""
    if not filters:
        return "", {}
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    if not start_date or not end_date:
        return "", {}
    week_col = f"{alias}.chart_week" if alias else "chart_week"
    return f" AND {week_col} BETWEEN :start_date AND :end_date", {
        "start_date": start_date,
        "end_date": end_date
    }

def render_sidebar_filters():
    """Render global sidebar filters for cross-page analysis."""
    st.sidebar.markdown("### Global Filters")
    bounds_df = get_chart_week_bounds()
    if bounds_df is None or bounds_df.empty:
        return {"start_date": None, "end_date": None, "top_n": 25}
    min_week = bounds_df.iloc[0]["min_week"]
    max_week = bounds_df.iloc[0]["max_week"]
    date_range = st.sidebar.date_input(
        "Chart week range",
        value=(min_week, max_week),
        min_value=min_week,
        max_value=max_week
    )
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_week, max_week
    top_n = st.sidebar.slider("Rows/series limit", min_value=10, max_value=100, value=25, step=5)
    st.sidebar.caption("Applies to Overview, Top Songs/Artists, Chart Trajectories, Time Trends, and Analysis Workbench.")
    return {
        "start_date": start_date,
        "end_date": end_date,
        "top_n": top_n
    }

def main():
    st.markdown('<h1 class="main-header">Billboard Charts Analysis Dashboard</h1>', unsafe_allow_html=True)
    st.caption("Explore chart performance, identify momentum shifts, and compare trends across time windows.")
    
    engine = get_db_engine()
    if not engine:
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    filters = render_sidebar_filters()
    page = st.sidebar.radio(
        "Choose a page",
        [
            "📊 Overview",
            "🏆 Top Songs & Artists",
            "🎸 Genre Analysis",
            "🎼 Audio Features",
            "📈 Chart Trajectories",
            "📅 Time Trends",
            "🔎 Analysis Workbench"
        ]
    )
    
    if page == "📊 Overview":
        show_overview(filters)
    elif page == "🏆 Top Songs & Artists":
        show_top_songs_artists(filters)
    elif page == "🎸 Genre Analysis":
        show_genre_analysis()
    elif page == "🎼 Audio Features":
        show_audio_features()
    elif page == "📈 Chart Trajectories":
        show_chart_trajectories(filters)
    elif page == "📅 Time Trends":
        show_time_trends(filters)
    elif page == "🔎 Analysis Workbench":
        show_analysis_workbench(filters)

def show_overview(filters):
    st.header("📊 Dashboard Overview")
    st.caption(
        f"Current window: {filters['start_date']} to {filters['end_date']} | Top N: {filters['top_n']}"
    )
    
    date_filter_plain, date_params = build_chart_week_filter(filters, alias=None)
    date_filter_ce, _ = build_chart_week_filter(filters, alias="ce")
    
    st.subheader("Key Metrics")
    metrics_query = """
    SELECT
        COUNT(DISTINCT chart_week) AS total_weeks,
        COUNT(*) AS total_entries,
        COUNT(DISTINCT song_id) AS unique_songs,
        COUNT(DISTINCT artist_id) AS unique_artists,
        SUM(CASE WHEN is_new THEN 1 ELSE 0 END) AS new_entries,
        AVG(COALESCE(weeks, 0)) AS avg_weeks_on_chart,
        AVG(rank) AS avg_rank,
        COUNT(DISTINCT CASE WHEN rank = 1 THEN COALESCE(song_id, title) END) AS unique_number_one_records
    FROM chart_entries
    WHERE chart_week IS NOT NULL
    """
    if date_filter_plain:
        metrics_query += date_filter_plain
    metrics_df = load_data(metrics_query, date_params if date_filter_plain else None)
    
    if metrics_df is not None and not metrics_df.empty:
        m = metrics_df.iloc[0]
        total_entries = int(m["total_entries"]) if pd.notna(m["total_entries"]) else 0
        new_entries = int(m["new_entries"]) if pd.notna(m["new_entries"]) else 0
        new_rate = (new_entries / total_entries * 100) if total_entries else 0
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Chart Weeks", f"{int(m['total_weeks']):,}")
        with c2:
            st.metric("Total Entries", f"{total_entries:,}")
        with c3:
            st.metric("New Entry Rate", f"{new_rate:.1f}%")
        with c4:
            st.metric("Avg Weeks on Chart", f"{float(m['avg_weeks_on_chart']):.1f}")
        
        c5, c6, c7 = st.columns(3)
        with c5:
            st.metric("Unique Songs", f"{int(m['unique_songs']):,}")
        with c6:
            st.metric("Unique Artists", f"{int(m['unique_artists']):,}")
        with c7:
            st.metric("Unique #1 Records", f"{int(m['unique_number_one_records']):,}")

    st.subheader("Churn vs Tenure Over Time")
    churn_query = """
    SELECT
        chart_week,
        SUM(CASE WHEN is_new THEN 1 ELSE 0 END) AS new_entries,
        AVG(COALESCE(weeks, 0)) AS avg_weeks_on_chart
    FROM chart_entries
    WHERE chart_week IS NOT NULL
    """
    if date_filter_plain:
        churn_query += date_filter_plain
    churn_query += """
    GROUP BY chart_week
    ORDER BY chart_week
    """
    churn_df = load_data(churn_query, date_params if date_filter_plain else None)
    
    if churn_df is not None and not churn_df.empty:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(
                x=churn_df["chart_week"],
                y=churn_df["new_entries"],
                mode="lines",
                name="New Entries",
                line=dict(color="#ff6b6b", width=2)
            ),
            secondary_y=False
        )
        fig.add_trace(
            go.Scatter(
                x=churn_df["chart_week"],
                y=churn_df["avg_weeks_on_chart"],
                mode="lines",
                name="Avg Weeks on Chart",
                line=dict(color="#1DB954", width=2)
            ),
            secondary_y=True
        )
        fig.update_layout(height=420, xaxis_title="Chart Week")
        fig.update_yaxes(title_text="New Entries", secondary_y=False)
        fig.update_yaxes(title_text="Avg Weeks on Chart", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Top Spot Turnover")
    number_one_query = """
    SELECT
        ce.chart_week,
        COALESCE(s.song_id, ce.song_id, ce.title) AS record_key,
        COALESCE(s.title, ce.title) AS song_title,
        COALESCE(a.name, ce.artist) AS artist_name
    FROM chart_entries ce
    LEFT JOIN songs s ON ce.song_id = s.song_id
    LEFT JOIN artists a ON ce.artist_id = a.artist_id
    WHERE ce.rank = 1
    """
    if date_filter_ce:
        number_one_query += date_filter_ce
    number_one_query += " ORDER BY ce.chart_week"
    number_one_df = load_data(number_one_query, date_params if date_filter_ce else None)
    
    if number_one_df is not None and not number_one_df.empty:
        number_one_df = number_one_df.sort_values("chart_week").copy()
        number_one_df["changed"] = (number_one_df["record_key"] != number_one_df["record_key"].shift(1)).astype(int)
        number_one_df.loc[number_one_df.index[0], "changed"] = 0
        number_one_df["rolling_turnover"] = number_one_df["changed"].rolling(12, min_periods=4).mean() * 100
        
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = px.line(
                number_one_df,
                x="chart_week",
                y="rolling_turnover",
                labels={"rolling_turnover": "12-Week #1 Turnover Rate (%)", "chart_week": "Chart Week"},
                title="How often does the #1 song change?"
            )
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            recent_changes = int(number_one_df["changed"].tail(52).sum()) if len(number_one_df) >= 52 else int(number_one_df["changed"].sum())
            st.metric("Recent #1 Changes", recent_changes)
            st.metric("All-Time #1 Changes", int(number_one_df["changed"].sum()))
            st.caption("Recent = last 52 available chart weeks in the selected window.")
    
    st.subheader("Artist Concentration")
    concentration_query = """
    WITH artist_share AS (
        SELECT
            ce.artist_id,
            COALESCE(a.name, ce.artist, 'Unknown Artist') AS artist_name,
            COUNT(*) AS chart_entries,
            COUNT(*)::numeric / SUM(COUNT(*)) OVER () AS entry_share
        FROM chart_entries ce
        LEFT JOIN artists a ON ce.artist_id = a.artist_id
        WHERE 1=1
    """
    if date_filter_ce:
        concentration_query += date_filter_ce
    concentration_query += """
        GROUP BY ce.artist_id, COALESCE(a.name, ce.artist, 'Unknown Artist')
    )
    SELECT
        artist_name,
        chart_entries,
        entry_share
    FROM artist_share
    ORDER BY chart_entries DESC
    LIMIT :top_n
    """
    concentration_params = {"top_n": filters["top_n"]}
    if date_filter_ce:
        concentration_params.update(date_params)
    concentration_df = load_data(concentration_query, concentration_params)
    
    if concentration_df is not None and not concentration_df.empty:
        concentration_df["entry_share_pct"] = concentration_df["entry_share"] * 100
        fig = px.bar(
            concentration_df.head(20),
            x="entry_share_pct",
            y="artist_name",
            orientation="h",
            color="chart_entries",
            labels={"entry_share_pct": "Share of Chart Entries (%)", "artist_name": "Artist"},
            title="Top Artists by Share of Chart Entries"
        )
        fig.update_layout(height=520, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Biggest Rank Improvements")
    movers_query = f"""
    WITH song_rank_path AS (
        SELECT
            ce.song_id,
            s.title,
            ce.chart_week,
            ce.rank,
            ROW_NUMBER() OVER (PARTITION BY ce.song_id ORDER BY ce.chart_week ASC) AS first_obs,
            ROW_NUMBER() OVER (PARTITION BY ce.song_id ORDER BY ce.chart_week DESC) AS last_obs
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.song_id
        WHERE ce.song_id IS NOT NULL
        {date_filter_ce}
    ),
    rank_summary AS (
        SELECT
            song_id,
            title,
            MIN(CASE WHEN first_obs = 1 THEN rank END) AS first_rank,
            MIN(CASE WHEN last_obs = 1 THEN rank END) AS latest_rank,
            MIN(rank) AS best_rank,
            COUNT(*) AS total_entries
        FROM song_rank_path
        GROUP BY song_id, title
    )
    SELECT
        title,
        first_rank,
        latest_rank,
        best_rank,
        total_entries,
        (first_rank - latest_rank) AS rank_change
    FROM rank_summary
    WHERE first_rank IS NOT NULL
      AND latest_rank IS NOT NULL
      AND total_entries >= 4
    ORDER BY rank_change DESC, best_rank ASC
    LIMIT :top_n
    """
    movers_params = {"top_n": filters["top_n"]}
    if date_filter_ce:
        movers_params.update(date_params)
    movers_df = load_data(movers_query, movers_params)
    if movers_df is not None and not movers_df.empty:
        st.dataframe(movers_df, use_container_width=True, hide_index=True)

def show_top_songs_artists(filters):
    st.header("🏆 Top Songs & Artists")
    st.caption(
        f"Current window: {filters['start_date']} to {filters['end_date']} | Top N: {filters['top_n']}"
    )
    date_filter_ce, date_params = build_chart_week_filter(filters, alias="ce")
    
    tab1, tab2, tab3 = st.tabs(["Top Songs", "Top Artists", "Song Performance"])
    
    with tab1:
        st.subheader("Most Successful Songs")
        
        top_songs_query = """
        SELECT 
            s.title,
            s.song_id,
            COUNT(DISTINCT ce.chart_week) as weeks_on_chart,
            MIN(ce.rank) as best_rank,
            MAX(ce.weeks) as max_weeks,
            STRING_AGG(DISTINCT a.name, ', ' ORDER BY a.name) as artists
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.song_id
        LEFT JOIN song_artists sa ON s.song_id = sa.song_id
        LEFT JOIN artists a ON sa.artist_id = a.artist_id
        WHERE ce.song_id IS NOT NULL
        """
        if date_filter_ce:
            top_songs_query += date_filter_ce
        top_songs_query += """
        GROUP BY s.song_id, s.title
        HAVING COUNT(DISTINCT ce.chart_week) > 0
        ORDER BY weeks_on_chart DESC, best_rank ASC
        LIMIT :top_n
        """
        
        songs_params = {"top_n": filters["top_n"]}
        if date_filter_ce:
            songs_params.update(date_params)
        songs_df = load_data(top_songs_query, songs_params)
        
        if songs_df is not None and not songs_df.empty:
            st.dataframe(
                songs_df[['title', 'artists', 'weeks_on_chart', 'best_rank', 'max_weeks']],
                use_container_width=True,
                hide_index=True
            )
            
            # Visualization
            top_20 = songs_df.head(20)
            fig = px.bar(
                top_20,
                x='weeks_on_chart',
                y='title',
                orientation='h',
                labels={'weeks_on_chart': 'Weeks on Chart', 'title': 'Song'},
                color='best_rank',
                color_continuous_scale='RdYlGn_r',
                title='Top 20 Songs by Weeks on Chart'
            )
            fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Most Successful Artists")
        
        top_artists_query = """
        SELECT 
            a.name as artist_name,
            COUNT(DISTINCT ce.song_id) as unique_songs,
            COUNT(DISTINCT ce.chart_week) as total_weeks,
            AVG(ce.rank) as avg_rank,
            MIN(ce.rank) as best_rank,
            a.tag as genre
        FROM chart_entries ce
        JOIN artists a ON ce.artist_id = a.artist_id
        WHERE ce.artist_id IS NOT NULL
        """
        if date_filter_ce:
            top_artists_query += date_filter_ce
        top_artists_query += """
        GROUP BY a.artist_id, a.name, a.tag
        HAVING COUNT(DISTINCT ce.chart_week) > 0
        ORDER BY unique_songs DESC, total_weeks DESC
        LIMIT :top_n
        """
        
        artist_params = {"top_n": filters["top_n"]}
        if date_filter_ce:
            artist_params.update(date_params)
        artists_df = load_data(top_artists_query, artist_params)
        
        if artists_df is not None and not artists_df.empty:
            st.dataframe(
                artists_df[['artist_name', 'genre', 'unique_songs', 'total_weeks', 'avg_rank', 'best_rank']],
                use_container_width=True,
                hide_index=True
            )
            
            # Visualization
            top_20 = artists_df.head(20)
            fig = px.scatter(
                top_20,
                x='unique_songs',
                y='total_weeks',
                size='unique_songs',
                color='avg_rank',
                hover_name='artist_name',
                labels={
                    'unique_songs': 'Number of Unique Songs',
                    'total_weeks': 'Total Weeks on Chart',
                    'avg_rank': 'Average Rank'
                },
                color_continuous_scale='RdYlGn_r',
                title='Top Artists: Songs vs Weeks on Chart'
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Song Performance Analysis")
        
        song_search_query = """
        SELECT DISTINCT s.title, s.song_id
        FROM songs s
        JOIN chart_entries ce ON s.song_id = ce.song_id
        WHERE 1=1
        """
        if date_filter_ce:
            song_search_query += date_filter_ce
        song_search_query += """
        ORDER BY s.title
        LIMIT 1000
        """
        
        all_songs = load_data(song_search_query, date_params if date_filter_ce else None)
        
        if all_songs is not None and not all_songs.empty:
            selected_song = st.selectbox(
                "Select a song to analyze",
                all_songs['title'].tolist()
            )
            
            if selected_song:
                song_id = all_songs[all_songs['title'] == selected_song]['song_id'].iloc[0]
                
                performance_query = """
                SELECT 
                    ce.chart_week,
                    ce.rank,
                    ce.weeks,
                    ce.peak_pos,
                    ce.is_new
                FROM chart_entries ce
                WHERE ce.song_id = :song_id
                """
                if date_filter_ce:
                    performance_query += date_filter_ce
                performance_query += """
                ORDER BY ce.chart_week
                """
                
                performance_params = {'song_id': song_id}
                if date_filter_ce:
                    performance_params.update(date_params)
                perf_df = load_data(performance_query, performance_params)
                
                if perf_df is not None and not perf_df.empty:
                    # Chart trajectory
                    fig = go.Figure()
                    
                    # Lower rank is better, so we'll invert for visualization
                    fig.add_trace(go.Scatter(
                        x=perf_df['chart_week'],
                        y=100 - perf_df['rank'] + 1,  # Invert so higher = better
                        mode='lines+markers',
                        name='Chart Position',
                        line=dict(color='#1DB954', width=2),
                        marker=dict(size=8)
                    ))
                    
                    fig.update_layout(
                        title=f'Chart Trajectory: {selected_song}',
                        xaxis_title='Chart Week',
                        yaxis_title='Chart Position (1=Best)',
                        height=400,
                        yaxis=dict(
                            tickmode='linear',
                            tick0=1,
                            dtick=10,
                            range=[0, 100],
                            autorange='reversed'
                        )
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Stats
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Best Rank", int(perf_df['rank'].min()))
                    with col2:
                        st.metric("Weeks on Chart", int(perf_df['weeks'].max()) if not perf_df['weeks'].isna().all() else 0)
                    with col3:
                        st.metric("Average Rank", f"{perf_df['rank'].mean():.1f}")
                    with col4:
                        st.metric("Total Appearances", len(perf_df))

def show_genre_analysis():
    st.header("🎸 Genre Analysis")
    
    genre_query = """
    SELECT 
        a.tag as genre,
        COUNT(DISTINCT ce.song_id) as unique_songs,
        COUNT(DISTINCT ce.artist_id) as unique_artists,
        COUNT(*) as total_appearances,
        AVG(ce.rank) as avg_rank,
        MIN(ce.rank) as best_rank
    FROM chart_entries ce
    JOIN artists a ON ce.artist_id = a.artist_id
    WHERE a.tag IS NOT NULL AND a.tag != ''
    GROUP BY a.tag
    HAVING COUNT(DISTINCT ce.song_id) >= 5
    ORDER BY unique_songs DESC
    """
    
    genres_df = load_data(genre_query)
    
    if genres_df is not None and not genres_df.empty:
        # Genre overview
        st.subheader("Genre Overview")
        st.dataframe(genres_df, use_container_width=True, hide_index=True)
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(
                genres_df.head(15),
                values='unique_songs',
                names='genre',
                title='Top 15 Genres by Number of Songs'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                genres_df.head(15),
                x='genre',
                y='avg_rank',
                labels={'genre': 'Genre', 'avg_rank': 'Average Chart Rank'},
                title='Average Chart Rank by Genre (Lower is Better)',
                color='avg_rank',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Genre trends over time
        st.subheader("Genre Trends Over Time")
        
        selected_genres = st.multiselect(
            "Select genres to compare",
            genres_df['genre'].tolist(),
            default=genres_df.head(5)['genre'].tolist()
        )
        
        if selected_genres:
            # Build query with proper escaping for SQL strings
            placeholders = ','.join([f"'{escape_sql_string(g)}'" for g in selected_genres])
            genre_trends_query = f"""
            SELECT 
                ce.chart_week,
                a.tag as genre,
                COUNT(DISTINCT ce.song_id) as song_count,
                AVG(ce.rank) as avg_rank
            FROM chart_entries ce
            JOIN artists a ON ce.artist_id = a.artist_id
            WHERE a.tag IN ({placeholders})
            GROUP BY ce.chart_week, a.tag
            ORDER BY ce.chart_week
            """
            
            genre_trends_df = load_data(genre_trends_query)
            
            if genre_trends_df is not None and not genre_trends_df.empty:
                fig = px.line(
                    genre_trends_df,
                    x='chart_week',
                    y='song_count',
                    color='genre',
                    labels={
                        'chart_week': 'Chart Week',
                        'song_count': 'Number of Songs',
                        'genre': 'Genre'
                    },
                    title='Number of Songs by Genre Over Time'
                )
                st.plotly_chart(fig, use_container_width=True)

def show_audio_features():
    st.header("🎼 Audio Features Analysis")
    
    # Check what audio features are available
    features_query = """
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'songs' 
    AND column_name IN ('danceability', 'energy', 'valence', 'tempo', 'acousticness', 
                        'instrumentalness', 'liveness', 'speechiness', 'loudness', 'key', 'mode')
    ORDER BY column_name
    """
    
    features_df = load_data(features_query)
    
    if features_df is not None and not features_df.empty:
        available_features = features_df['column_name'].tolist()
        
        st.subheader("Audio Features Distribution")
        
        # Build query dynamically based on available features
        feature_cols = ', '.join([f"s.{f}" for f in available_features])
        
        audio_query = f"""
        SELECT 
            {feature_cols},
            ce.chart_week,
            ce.rank,
            a.tag as genre
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.song_id
        LEFT JOIN artists a ON ce.artist_id = a.artist_id
        WHERE ce.song_id IS NOT NULL
        """
        
        audio_df = load_data(audio_query)
        
        if audio_df is not None and not audio_df.empty:
            # Feature selector
            selected_feature = st.selectbox("Select audio feature to analyze", available_features)
            
            if selected_feature:
                # Remove null values for selected feature
                feature_df = audio_df[audio_df[selected_feature].notna()].copy()
                
                if not feature_df.empty:
                    # Distribution
                    fig = px.histogram(
                        feature_df,
                        x=selected_feature,
                        nbins=50,
                        title=f'Distribution of {selected_feature.title()}',
                        labels={selected_feature: selected_feature.title(), 'count': 'Number of Songs'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Feature vs Chart Performance
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.scatter(
                            feature_df,
                            x=selected_feature,
                            y='rank',
                            color='genre',
                            labels={
                                selected_feature: selected_feature.title(),
                                'rank': 'Chart Rank',
                                'genre': 'Genre'
                            },
                            title=f'{selected_feature.title()} vs Chart Rank',
                            trendline='ols'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Feature trends over time
                        feature_trends = feature_df.groupby('chart_week')[selected_feature].mean().reset_index()
                        fig = px.line(
                            feature_trends,
                            x='chart_week',
                            y=selected_feature,
                            title=f'Average {selected_feature.title()} Over Time',
                            labels={
                                'chart_week': 'Chart Week',
                                selected_feature: f'Average {selected_feature.title()}'
                            }
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
            # Correlation matrix
            st.subheader("Audio Features Correlation")
            
            numeric_features = [f for f in available_features if f not in ['key', 'mode']]
            if len(numeric_features) >= 2:
                corr_df = audio_df[numeric_features].corr()
                fig = px.imshow(
                    corr_df,
                    labels=dict(x="Feature", y="Feature", color="Correlation"),
                    x=corr_df.columns,
                    y=corr_df.columns,
                    color_continuous_scale='RdBu',
                    aspect="auto",
                    title="Audio Features Correlation Matrix"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Extreme Outliers Section
            st.subheader("🔍 Extreme Outliers")
            st.markdown("Songs with unusually high or low values in audio features")
            
            # Get songs with all their features for outlier detection
            outliers_query = """
            SELECT DISTINCT
                s.song_id,
                s.title,
                s.danceability,
                s.energy,
                s.valence,
                s.tempo,
                s.acousticness,
                s.instrumentalness,
                s.liveness,
                s.speechiness,
                s.loudness, 
                STRING_AGG(DISTINCT a.name, ', ' ORDER BY a.name) as artists,
                MIN(ce.rank) as best_rank
            FROM songs s
            JOIN chart_entries ce ON s.song_id = ce.song_id
            LEFT JOIN song_artists sa ON s.song_id = sa.song_id
            LEFT JOIN artists a ON sa.artist_id = a.artist_id
            WHERE s.song_id IS NOT NULL
            GROUP BY s.song_id, s.title, s.danceability, s.energy, s.valence, s.tempo,
                     s.acousticness, s.instrumentalness, s.liveness, s.speechiness, s.loudness
            """
            
            outliers_df = load_data(outliers_query)
            
            if outliers_df is not None and not outliers_df.empty:
                # Filter to numeric features that exist in the data
                numeric_features_available = [f for f in numeric_features if f in outliers_df.columns]
                
                if len(numeric_features_available) > 0:
                    # Calculate outliers using IQR method
                    outlier_songs = []
                    
                    for feature in numeric_features_available:
                        feature_data = outliers_df[feature].dropna()
                        
                        if len(feature_data) > 0:
                            Q1 = feature_data.quantile(0.25)
                            Q3 = feature_data.quantile(0.75)
                            IQR = Q3 - Q1
                            
                            # Define outlier bounds (using 1.5 * IQR rule, but we'll be more strict)
                            lower_bound = Q1 - 2.5 * IQR  # More extreme outliers
                            upper_bound = Q3 + 2.5 * IQR
                            
                            # Find songs that are outliers
                            feature_outliers = outliers_df[
                                (outliers_df[feature] < lower_bound) | 
                                (outliers_df[feature] > upper_bound)
                            ].copy()
                            
                            if not feature_outliers.empty:
                                feature_outliers['outlier_feature'] = feature
                                feature_outliers['outlier_value'] = feature_outliers[feature]
                                feature_outliers['outlier_type'] = feature_outliers[feature].apply(
                                    lambda x: 'Very Low' if x < lower_bound else 'Very High'
                                )
                                feature_outliers['percentile'] = feature_outliers[feature].apply(
                                    lambda x: (feature_data < x).sum() / len(feature_data) * 100
                                )
                                
                                # Select relevant columns
                                outlier_cols = ['song_id', 'title', 'artists', 'outlier_feature', 'outlier_value', 
                                               'outlier_type', 'percentile', 'best_rank']
                                available_cols = [c for c in outlier_cols if c in feature_outliers.columns]
                                
                                outlier_songs.append(feature_outliers[available_cols])
                    
                    if outlier_songs:
                        all_outliers = pd.concat(outlier_songs, ignore_index=True)
                        
                        # Sort by how extreme the outlier is (percentile closest to 0 or 100)
                        all_outliers['extremeness'] = all_outliers['percentile'].apply(
                            lambda x: min(x, 100 - x)
                        )
                        all_outliers = all_outliers.sort_values('extremeness', ascending=True)
                        
                        # Group by song to show all outlier features per song
                        st.markdown("**Songs with extreme audio feature values:**")
                        
                        # Create tabs for different views
                        tab1, tab2 = st.tabs(["By Song", "By Feature"])
                        
                        with tab1:
                            # Group by song
                            for idx, row in all_outliers.head(50).iterrows():
                                with st.expander(f"🎵 {row['title']} - {row['artists'] if pd.notna(row.get('artists')) else 'Unknown Artist'}"):
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("Feature", row['outlier_feature'].title())
                                    with col3:
                                        st.metric("Value", f"{row['outlier_value']:.4f}")
                                    with col4:
                                        st.metric("Type", row['outlier_type'])
                                    
                                    percentile = row['percentile']
                                    if percentile < 1:
                                        st.info(f"⚠️ This song is in the **bottom {percentile:.2f}%** of all songs for {row['outlier_feature']}")
                                    elif percentile > 99:
                                        st.info(f"⚠️ This song is in the **top {100-percentile:.2f}%** of all songs for {row['outlier_feature']}")
                                    
                                    if pd.notna(row.get('best_rank')):
                                        st.caption(f"Best chart position: #{int(row['best_rank'])}")
                        
                        with tab2:
                            # Group by feature
                            feature_selector = st.selectbox(
                                "Select feature to view outliers",
                                numeric_features_available,
                                key="outlier_feature_selector"
                            )
                            
                            feature_outliers_filtered = all_outliers[
                                all_outliers['outlier_feature'] == feature_selector
                            ].sort_values('outlier_value', ascending=False)
                            
                            if not feature_outliers_filtered.empty:
                                st.markdown(f"**Extreme outliers for {feature_selector}:**")
                                
                                # Create visualization
                                fig = px.bar(
                                    feature_outliers_filtered.head(20),
                                    x='outlier_value',
                                    y='title',
                                    orientation='h',
                                    color='outlier_type',
                                    color_discrete_map={'Very High': '#ff6b6b', 'Very Low': '#4ecdc4'},
                                    labels={
                                        'outlier_value': f'{feature_selector.title()} Value',
                                        'title': 'Song',
                                        'outlier_type': 'Type'
                                    },
                                    title=f'Top 20 Extreme Outliers for {feature_selector.title()}',
                                    hover_data=['song_id', 'artists', 'best_rank']
                                )
                                fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Table view
                                display_cols = ['title', 'song_id', 'artists', 'outlier_value', 'outlier_type', 'best_rank']
                                available_display_cols = [c for c in display_cols if c in feature_outliers_filtered.columns]
                                st.dataframe(
                                    feature_outliers_filtered[available_display_cols].head(30),
                                    use_container_width=True,
                                    hide_index=True
                                )
                            else:
                                st.info(f"No extreme outliers found for {feature_selector}")
                    else:
                        st.info("No extreme outliers found in the dataset.")
                else:
                    st.info("No numeric audio features available for outlier analysis.")
            else:
                st.info("No song data available for outlier analysis.")
    else:
        st.info("No audio features found in the database. Audio features may not have been ingested yet.")

def show_chart_trajectories(filters):
    st.header("📈 Chart Trajectories")
    st.caption(
        f"Current window: {filters['start_date']} to {filters['end_date']} | Top N: {filters['top_n']}"
    )
    date_filter_ce, date_params = build_chart_week_filter(filters, alias="ce")
    
    trajectory_query = """
    SELECT 
        s.title,
        s.song_id,
        COUNT(DISTINCT ce.chart_week) as total_weeks,
        MIN(ce.rank) as best_rank
    FROM chart_entries ce
    JOIN songs s ON ce.song_id = s.song_id
    WHERE ce.song_id IS NOT NULL
    """
    if date_filter_ce:
        trajectory_query += date_filter_ce
    trajectory_query += """
    GROUP BY s.song_id, s.title
    HAVING COUNT(DISTINCT ce.chart_week) >= 10
    ORDER BY best_rank ASC, total_weeks DESC
    LIMIT :top_n
    """
    
    trajectory_params = {"top_n": filters["top_n"]}
    if date_filter_ce:
        trajectory_params.update(date_params)
    songs_df = load_data(trajectory_query, trajectory_params)
    
    if songs_df is not None and not songs_df.empty:
        selected_songs = st.multiselect(
            "Select songs to compare (showing songs with 10+ weeks on chart)",
            songs_df['title'].tolist(),
            default=songs_df.head(5)['title'].tolist()
        )
        
        if selected_songs:
            song_ids = songs_df[songs_df['title'].isin(selected_songs)]['song_id'].tolist()
            
            # Build query for selected songs with proper escaping
            placeholders = ','.join([f"'{escape_sql_string(sid)}'" for sid in song_ids])
            trajectory_detail_query = f"""
            SELECT 
                s.title,
                ce.chart_week,
                ce.rank,
                ce.weeks
            FROM chart_entries ce
            JOIN songs s ON ce.song_id = s.song_id
            WHERE ce.song_id IN ({placeholders})
            """
            if date_filter_ce:
                trajectory_detail_query += date_filter_ce
            trajectory_detail_query += """
            ORDER BY s.title, ce.chart_week
            """
            
            traj_df = load_data(trajectory_detail_query, date_params if date_filter_ce else None)
            
            if traj_df is not None and not traj_df.empty:
                fig = px.line(
                    traj_df,
                    x='chart_week',
                    y='rank',
                    color='title',
                    labels={
                        'chart_week': 'Chart Week',
                        'rank': 'Chart Position',
                        'title': 'Song'
                    },
                    title='Chart Trajectories Comparison (Lower Rank = Better Position)',
                    markers=True
                )
                fig.update_yaxes(autorange='reversed')  # Invert y-axis so 1 is at top
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # Trajectory patterns
                st.subheader("Trajectory Patterns")
                
                # Calculate trajectory metrics
                pattern_data = []
                for song in selected_songs:
                    song_data = traj_df[traj_df['title'] == song].sort_values('chart_week')
                    if len(song_data) > 1:
                        first_rank = song_data.iloc[0]['rank']
                        last_rank = song_data.iloc[-1]['rank']
                        best_rank = song_data['rank'].min()
                        worst_rank = song_data['rank'].max()
                        
                        pattern_data.append({
                            'Song': song,
                            'First Rank': first_rank,
                            'Last Rank': last_rank,
                            'Best Rank': best_rank,
                            'Worst Rank': worst_rank,
                            'Total Weeks': len(song_data),
                            'Trend': 'Rising' if last_rank < first_rank else 'Falling' if last_rank > first_rank else 'Stable'
                        })
                
                if pattern_data:
                    pattern_df = pd.DataFrame(pattern_data)
                    st.dataframe(pattern_df, use_container_width=True, hide_index=True)

def show_analysis_workbench(filters):
    st.header("🔎 Analysis Workbench")
    st.caption("Purpose-built views for comparison and actionable trend analysis.")
    date_filter_ce, date_params = build_chart_week_filter(filters, alias="ce")

    start_ts = pd.to_datetime(filters["start_date"])
    end_ts = pd.to_datetime(filters["end_date"])
    midpoint = start_ts + (end_ts - start_ts) / 2

    st.subheader("Period Comparison")
    left_col, right_col = st.columns(2)

    comparison_query = """
    SELECT
        COUNT(DISTINCT ce.song_id) AS unique_songs,
        COUNT(DISTINCT ce.artist_id) AS unique_artists,
        COUNT(*) AS total_entries,
        AVG(ce.rank) AS avg_rank,
        SUM(CASE WHEN ce.rank = 1 THEN 1 ELSE 0 END) AS number_one_weeks
    FROM chart_entries ce
    WHERE ce.chart_week BETWEEN :period_start AND :period_end
    """

    period_a = load_data(
        comparison_query,
        {"period_start": start_ts.date(), "period_end": midpoint.date()}
    )
    period_b = load_data(
        comparison_query,
        {"period_start": (midpoint + timedelta(days=1)).date(), "period_end": end_ts.date()}
    )

    if period_a is not None and period_b is not None and not period_a.empty and not period_b.empty:
        a = period_a.iloc[0]
        b = period_b.iloc[0]
        avg_rank_a = float(a["avg_rank"]) if pd.notna(a["avg_rank"]) else 0.0
        avg_rank_b = float(b["avg_rank"]) if pd.notna(b["avg_rank"]) else 0.0
        with left_col:
            st.markdown(f"**Period A:** {start_ts.date()} to {midpoint.date()}")
            st.metric("Unique Songs", f"{int(a['unique_songs']):,}")
            st.metric("Unique Artists", f"{int(a['unique_artists']):,}")
            st.metric("Average Rank", f"{avg_rank_a:.2f}")
        with right_col:
            st.markdown(f"**Period B:** {(midpoint + timedelta(days=1)).date()} to {end_ts.date()}")
            st.metric("Unique Songs", f"{int(b['unique_songs']):,}", delta=int(b['unique_songs'] - a['unique_songs']))
            st.metric("Unique Artists", f"{int(b['unique_artists']):,}", delta=int(b['unique_artists'] - a['unique_artists']))
            st.metric("Average Rank", f"{avg_rank_b:.2f}", delta=f"{(avg_rank_a - avg_rank_b):.2f} better")

    st.subheader("Genre Momentum (Improving vs Declining)")
    momentum_query = f"""
    SELECT
        a.tag AS genre,
        COUNT(*) AS observations,
        AVG(ce.rank) AS avg_rank,
        REGR_SLOPE(ce.rank, EXTRACT(EPOCH FROM ce.chart_week)) AS rank_slope
    FROM chart_entries ce
    JOIN artists a ON ce.artist_id = a.artist_id
    WHERE a.tag IS NOT NULL AND a.tag != ''
    {date_filter_ce}
    GROUP BY a.tag
    HAVING COUNT(*) >= 20
    ORDER BY rank_slope ASC
    LIMIT :top_n
    """
    momentum_params = {"top_n": filters["top_n"]}
    if date_filter_ce:
        momentum_params.update(date_params)
    momentum_df = load_data(momentum_query, momentum_params)

    if momentum_df is not None and not momentum_df.empty:
        fig = px.scatter(
            momentum_df,
            x="rank_slope",
            y="avg_rank",
            size="observations",
            color="rank_slope",
            hover_name="genre",
            labels={
                "rank_slope": "Rank Slope Over Time (negative = improving)",
                "avg_rank": "Average Rank"
            },
            color_continuous_scale="RdYlGn_r",
            title="Genre Momentum Map"
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=480)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(momentum_df, use_container_width=True, hide_index=True)

    st.subheader("Artist Efficiency")
    efficiency_query = f"""
    SELECT
        a.name AS artist_name,
        COUNT(DISTINCT ce.song_id) AS unique_songs,
        COUNT(*) AS total_entries,
        AVG(ce.rank) AS avg_rank,
        MIN(ce.rank) AS best_rank
    FROM chart_entries ce
    JOIN artists a ON ce.artist_id = a.artist_id
    WHERE ce.artist_id IS NOT NULL
    {date_filter_ce}
    GROUP BY a.artist_id, a.name
    HAVING COUNT(*) >= 10
    ORDER BY unique_songs DESC, total_entries DESC
    LIMIT :top_n
    """
    efficiency_params = {"top_n": filters["top_n"]}
    if date_filter_ce:
        efficiency_params.update(date_params)
    efficiency_df = load_data(efficiency_query, efficiency_params)
    if efficiency_df is not None and not efficiency_df.empty:
        fig = px.scatter(
            efficiency_df,
            x="unique_songs",
            y="avg_rank",
            size="total_entries",
            color="best_rank",
            hover_name="artist_name",
            labels={
                "unique_songs": "Unique Songs",
                "avg_rank": "Average Rank",
                "best_rank": "Best Rank"
            },
            color_continuous_scale="RdYlGn_r",
            title="Artist Output vs Efficiency"
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

def show_time_trends(filters):
    st.header("📅 Time-Based Trends")
    st.caption(
        f"Current window: {filters['start_date']} to {filters['end_date']} | Top N: {filters['top_n']}"
    )
    date_filter_ce, date_params = build_chart_week_filter(filters, alias="ce")
    
    tab1, tab2, tab3 = st.tabs(["Yearly Dynamics", "Rank Mobility", "Seasonality"])
    
    with tab1:
        st.subheader("Yearly Dynamics")
        
        yearly_query = """
        SELECT 
            EXTRACT(YEAR FROM ce.chart_week) as year,
            COUNT(*) as total_entries,
            SUM(CASE WHEN ce.is_new THEN 1 ELSE 0 END) as new_entries,
            AVG(COALESCE(ce.weeks, 0)) as avg_weeks_on_chart,
            COUNT(DISTINCT CASE WHEN ce.rank = 1 THEN COALESCE(ce.song_id, ce.title) END) as unique_number_one_records
        FROM chart_entries ce
        WHERE ce.chart_week IS NOT NULL
        """
        if date_filter_ce:
            yearly_query += date_filter_ce
        yearly_query += """
        GROUP BY EXTRACT(YEAR FROM ce.chart_week)
        ORDER BY year
        """
        
        yearly_df = load_data(yearly_query, date_params if date_filter_ce else None)
        
        if yearly_df is not None and not yearly_df.empty:
            yearly_df["new_entry_rate"] = yearly_df["new_entries"] / yearly_df["total_entries"] * 100
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=(
                    "New Entry Rate (%)",
                    "Average Weeks on Chart",
                    "Unique #1 Records",
                    "Total Entries"
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=yearly_df["year"],
                    y=yearly_df["new_entry_rate"],
                    mode="lines+markers",
                    line=dict(color="#ff6b6b")
                ),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=yearly_df["year"],
                    y=yearly_df["avg_weeks_on_chart"],
                    mode="lines+markers",
                    line=dict(color="#1DB954")
                ),
                row=1, col=2
            )
            fig.add_trace(
                go.Bar(
                    x=yearly_df["year"],
                    y=yearly_df["unique_number_one_records"],
                    marker_color="#4ecdc4"
                ),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(
                    x=yearly_df["year"],
                    y=yearly_df["total_entries"],
                    marker_color="#1ed760"
                ),
                row=2, col=2
            )
            
            fig.update_layout(height=700, showlegend=False)
            fig.update_xaxes(title_text="Year")
            
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Rank Mobility")
        
        mobility_query = """
        WITH ranked AS (
            SELECT
                ce.song_id,
                ce.chart_week,
                ce.rank,
                LAG(ce.rank) OVER (PARTITION BY ce.song_id ORDER BY ce.chart_week) AS prev_rank
            FROM chart_entries ce
            WHERE ce.song_id IS NOT NULL
        ),
        deltas AS (
            SELECT
                EXTRACT(YEAR FROM chart_week) AS year,
                (prev_rank - rank) AS rank_delta
            FROM ranked
            WHERE prev_rank IS NOT NULL
        )
        SELECT
            year,
            AVG(rank_delta) AS avg_rank_delta,
            SUM(CASE WHEN rank_delta >= 10 THEN 1 ELSE 0 END) AS big_jumps,
            SUM(CASE WHEN rank_delta <= -10 THEN 1 ELSE 0 END) AS big_drops,
            COUNT(*) AS comparable_rows
        FROM deltas
        WHERE 1=1
        """
        if date_filter_ce:
            mobility_query += date_filter_ce.replace("ce.chart_week", "chart_week")
        mobility_query += """
        GROUP BY year
        ORDER BY year
        """
        
        mobility_df = load_data(mobility_query, date_params if date_filter_ce else None)
        
        if mobility_df is not None and not mobility_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.line(
                    mobility_df,
                    x="year",
                    y="avg_rank_delta",
                    markers=True,
                    labels={"avg_rank_delta": "Average Week-over-Week Rank Improvement", "year": "Year"},
                    title="Do songs generally improve or decline week to week?"
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    mobility_df,
                    x="year",
                    y=["big_jumps", "big_drops"],
                    barmode="group",
                    labels={"value": "Count", "year": "Year", "variable": "Event"},
                    title="Large Weekly Moves (10+ spots)"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Seasonality")
        
        seasonal_query = """
        WITH monthly_base AS (
            SELECT
                EXTRACT(MONTH FROM ce.chart_week) AS month,
                AVG(COALESCE(ce.weeks, 0)) AS avg_weeks_on_chart,
                AVG(CASE WHEN ce.is_new THEN 1 ELSE 0 END) * 100 AS new_entry_rate
            FROM chart_entries ce
            WHERE ce.chart_week IS NOT NULL
        """
        if date_filter_ce:
            seasonal_query += date_filter_ce
        seasonal_query += """
            GROUP BY EXTRACT(MONTH FROM ce.chart_week)
        ),
        number_one AS (
            SELECT
                ce.chart_week,
                EXTRACT(MONTH FROM ce.chart_week) AS month,
                COALESCE(ce.song_id, ce.title) AS record_key
            FROM chart_entries ce
            WHERE ce.rank = 1
        """
        if date_filter_ce:
            seasonal_query += date_filter_ce
        seasonal_query += """
        ),
        number_one_changes AS (
            SELECT
                month,
                CASE
                    WHEN record_key != LAG(record_key) OVER (ORDER BY chart_week) THEN 1
                    ELSE 0
                END AS changed
            FROM number_one
        ),
        monthly_turnover AS (
            SELECT
                month,
                AVG(COALESCE(changed, 0)) * 100 AS number_one_change_rate
            FROM number_one_changes
            GROUP BY month
        )
        SELECT
            mb.month,
            mb.avg_weeks_on_chart,
            mb.new_entry_rate,
            COALESCE(mt.number_one_change_rate, 0) AS number_one_change_rate
        FROM monthly_base mb
        LEFT JOIN monthly_turnover mt ON mb.month = mt.month
        ORDER BY mb.month
        """
        
        seasonal_df = load_data(seasonal_query, date_params if date_filter_ce else None)
        
        if seasonal_df is not None and not seasonal_df.empty:
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            seasonal_df['month_name'] = seasonal_df['month'].apply(lambda x: month_names[int(x) - 1])

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(
                go.Bar(
                    x=seasonal_df["month_name"],
                    y=seasonal_df["new_entry_rate"],
                    name="New Entry Rate (%)",
                    marker_color="#ff6b6b"
                ),
                secondary_y=False
            )
            fig.add_trace(
                go.Scatter(
                    x=seasonal_df["month_name"],
                    y=seasonal_df["avg_weeks_on_chart"],
                    mode="lines+markers",
                    name="Avg Weeks on Chart",
                    line=dict(color="#1DB954", width=2)
                ),
                secondary_y=True
            )
            fig.add_trace(
                go.Scatter(
                    x=seasonal_df["month_name"],
                    y=seasonal_df["number_one_change_rate"],
                    mode="lines+markers",
                    name="#1 Change Rate (%)",
                    line=dict(color="#4ecdc4", width=2, dash="dot")
                ),
                secondary_y=False
            )
            fig.update_layout(height=520, title="Monthly Stability vs Refresh")
            fig.update_yaxes(title_text="Rates (%)", secondary_y=False)
            fig.update_yaxes(title_text="Avg Weeks on Chart", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
