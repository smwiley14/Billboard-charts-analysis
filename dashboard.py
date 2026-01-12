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

def main():
    st.markdown('<h1 class="main-header">🎵 Billboard Charts Analysis Dashboard</h1>', unsafe_allow_html=True)
    
    engine = get_db_engine()
    if not engine:
        st.stop()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Choose a page",
        ["📊 Overview", "🏆 Top Songs & Artists", "🎸 Genre Analysis", "🎼 Audio Features", "📈 Chart Trajectories", "📅 Time Trends"]
    )
    
    if page == "📊 Overview":
        show_overview()
    elif page == "🏆 Top Songs & Artists":
        show_top_songs_artists()
    elif page == "🎸 Genre Analysis":
        show_genre_analysis()
    elif page == "🎼 Audio Features":
        show_audio_features()
    elif page == "📈 Chart Trajectories":
        show_chart_trajectories()
    elif page == "📅 Time Trends":
        show_time_trends()

def show_overview():
    st.header("📊 Dashboard Overview")
    
    # Key Metrics
    st.subheader("Key Metrics")
    
    metrics_query = """
    SELECT 
        COUNT(DISTINCT chart_week) as total_weeks,
        COUNT(DISTINCT song_id) as total_songs,
        COUNT(DISTINCT artist_id) as total_artists,
        MIN(chart_week) as earliest_week,
        MAX(chart_week) as latest_week,
        COUNT(*) as total_chart_entries
    FROM chart_entries
    WHERE chart_week IS NOT NULL
    """
    
    metrics_df = load_data(metrics_query)
    
    if metrics_df is not None and not metrics_df.empty:
        metrics = metrics_df.iloc[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Chart Weeks", f"{metrics['total_weeks']:,}")
        
        with col2:
            st.metric("Unique Songs", f"{metrics['total_songs']:,}")
        
        with col3:
            st.metric("Unique Artists", f"{metrics['total_artists']:,}")
        
        with col4:
            st.metric("Total Chart Entries", f"{metrics['total_chart_entries']:,}")
        
        col5, col6 = st.columns(2)
        with col5:
            st.metric("Earliest Week", str(metrics['earliest_week']))
        with col6:
            st.metric("Latest Week", str(metrics['latest_week']))
    
    # Data Coverage Chart
    st.subheader("📅 Data Coverage Over Time")
    
    coverage_query = """
    SELECT 
        chart_week,
        COUNT(DISTINCT song_id) as unique_songs,
        COUNT(*) as total_entries
    FROM chart_entries
    WHERE chart_week IS NOT NULL
    GROUP BY chart_week
    ORDER BY chart_week
    """
    
    coverage_df = load_data(coverage_query)
    
    if coverage_df is not None and not coverage_df.empty:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Unique Songs Per Week", "Total Chart Entries Per Week"),
            vertical_spacing=0.1
        )
        
        fig.add_trace(
            go.Scatter(
                x=coverage_df['chart_week'],
                y=coverage_df['unique_songs'],
                mode='lines',
                name='Unique Songs',
                line=dict(color='#1DB954', width=2)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=coverage_df['chart_week'],
                y=coverage_df['total_entries'],
                mode='lines',
                name='Total Entries',
                line=dict(color='#1ed760', width=2)
            ),
            row=2, col=1
        )
        
        fig.update_layout(height=600, showlegend=False)
        fig.update_xaxes(title_text="Chart Week", row=2, col=1)
        fig.update_yaxes(title_text="Count", row=1, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Top Genres Quick View
    st.subheader("🎸 Top Genres")
    
    top_genres_query = """
    SELECT 
        a.tag as genre,
        COUNT(DISTINCT ce.song_id) as song_count,
        COUNT(DISTINCT ce.artist_id) as artist_count
    FROM chart_entries ce
    JOIN artists a ON ce.artist_id = a.artist_id
    WHERE a.tag IS NOT NULL AND a.tag != ''
    GROUP BY a.tag
    ORDER BY song_count DESC
    LIMIT 10
    """
    
    genres_df = load_data(top_genres_query)
    
    if genres_df is not None and not genres_df.empty:
        fig = px.bar(
            genres_df,
            x='song_count',
            y='genre',
            orientation='h',
            labels={'song_count': 'Number of Songs', 'genre': 'Genre'},
            color='song_count',
            color_continuous_scale='Greens'
        )
        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

def show_top_songs_artists():
    st.header("🏆 Top Songs & Artists")
    
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
        GROUP BY s.song_id, s.title
        HAVING COUNT(DISTINCT ce.chart_week) > 0
        ORDER BY weeks_on_chart DESC, best_rank ASC
        LIMIT 50
        """
        
        songs_df = load_data(top_songs_query)
        
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
        GROUP BY a.artist_id, a.name, a.tag
        HAVING COUNT(DISTINCT ce.chart_week) > 0
        ORDER BY unique_songs DESC, total_weeks DESC
        LIMIT 50
        """
        
        artists_df = load_data(top_artists_query)
        
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
        ORDER BY s.title
        LIMIT 1000
        """
        
        all_songs = load_data(song_search_query)
        
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
                ORDER BY ce.chart_week
                """
                
                perf_df = load_data(performance_query, {'song_id': song_id})
                
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
    else:
        st.info("No audio features found in the database. Audio features may not have been ingested yet.")

def show_chart_trajectories():
    st.header("📈 Chart Trajectories")
    
    trajectory_query = """
    SELECT 
        s.title,
        s.song_id,
        COUNT(DISTINCT ce.chart_week) as total_weeks,
        MIN(ce.rank) as best_rank
    FROM chart_entries ce
    JOIN songs s ON ce.song_id = s.song_id
    WHERE ce.song_id IS NOT NULL
    GROUP BY s.song_id, s.title
    HAVING COUNT(DISTINCT ce.chart_week) >= 10
    ORDER BY best_rank ASC, total_weeks DESC
    LIMIT 100
    """
    
    songs_df = load_data(trajectory_query)
    
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
            ORDER BY s.title, ce.chart_week
            """
            
            traj_df = load_data(trajectory_detail_query)
            
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

def show_time_trends():
    st.header("📅 Time-Based Trends")
    
    tab1, tab2, tab3 = st.tabs(["Yearly Trends", "Decade Comparison", "Seasonal Patterns"])
    
    with tab1:
        st.subheader("Yearly Trends")
        
        yearly_query = """
        SELECT 
            EXTRACT(YEAR FROM ce.chart_week) as year,
            COUNT(DISTINCT ce.song_id) as unique_songs,
            COUNT(DISTINCT ce.artist_id) as unique_artists,
            AVG(ce.rank) as avg_rank
        FROM chart_entries ce
        WHERE ce.chart_week IS NOT NULL
        GROUP BY EXTRACT(YEAR FROM ce.chart_week)
        ORDER BY year
        """
        
        yearly_df = load_data(yearly_query)
        
        if yearly_df is not None and not yearly_df.empty:
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=("Unique Songs Per Year", "Unique Artists Per Year", 
                               "Average Chart Rank Per Year", "Songs vs Artists Ratio"),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Unique songs
            fig.add_trace(
                go.Scatter(x=yearly_df['year'], y=yearly_df['unique_songs'], 
                          mode='lines+markers', name='Unique Songs', line=dict(color='#1DB954')),
                row=1, col=1
            )
            
            # Unique artists
            fig.add_trace(
                go.Scatter(x=yearly_df['year'], y=yearly_df['unique_artists'], 
                          mode='lines+markers', name='Unique Artists', line=dict(color='#1ed760')),
                row=1, col=2
            )
            
            # Average rank
            fig.add_trace(
                go.Scatter(x=yearly_df['year'], y=yearly_df['avg_rank'], 
                          mode='lines+markers', name='Avg Rank', line=dict(color='#ff6b6b')),
                row=2, col=1
            )
            
            # Ratio
            yearly_df['ratio'] = yearly_df['unique_songs'] / yearly_df['unique_artists']
            fig.add_trace(
                go.Scatter(x=yearly_df['year'], y=yearly_df['ratio'], 
                          mode='lines+markers', name='Songs/Artists', line=dict(color='#4ecdc4')),
                row=2, col=2
            )
            
            fig.update_layout(height=700, showlegend=False)
            fig.update_xaxes(title_text="Year", row=2, col=1)
            fig.update_xaxes(title_text="Year", row=2, col=2)
            fig.update_yaxes(title_text="Count", row=1, col=1)
            fig.update_yaxes(title_text="Count", row=1, col=2)
            fig.update_yaxes(title_text="Average Rank", row=2, col=1)
            fig.update_yaxes(title_text="Ratio", row=2, col=2)
            
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Decade Comparison")
        
        decade_query = """
        SELECT 
            CASE 
                WHEN EXTRACT(YEAR FROM ce.chart_week) < 2010 THEN '2000s'
                WHEN EXTRACT(YEAR FROM ce.chart_week) < 2020 THEN '2010s'
                ELSE '2020s'
            END as decade,
            COUNT(DISTINCT ce.song_id) as unique_songs,
            COUNT(DISTINCT ce.artist_id) as unique_artists,
            AVG(ce.rank) as avg_rank
        FROM chart_entries ce
        WHERE ce.chart_week IS NOT NULL
        GROUP BY decade
        ORDER BY decade
        """
        
        decade_df = load_data(decade_query)
        
        if decade_df is not None and not decade_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    decade_df,
                    x='decade',
                    y=['unique_songs', 'unique_artists'],
                    barmode='group',
                    labels={'value': 'Count', 'decade': 'Decade', 'variable': 'Type'},
                    title='Unique Songs and Artists by Decade'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    decade_df,
                    x='decade',
                    y='avg_rank',
                    labels={'avg_rank': 'Average Chart Rank', 'decade': 'Decade'},
                    title='Average Chart Rank by Decade',
                    color='avg_rank',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Seasonal Patterns")
        
        seasonal_query = """
        SELECT 
            EXTRACT(MONTH FROM ce.chart_week) as month,
            COUNT(DISTINCT ce.song_id) as unique_songs,
            AVG(ce.rank) as avg_rank
        FROM chart_entries ce
        WHERE ce.chart_week IS NOT NULL
        GROUP BY EXTRACT(MONTH FROM ce.chart_week)
        ORDER BY month
        """
        
        seasonal_df = load_data(seasonal_query)
        
        if seasonal_df is not None and not seasonal_df.empty:
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            seasonal_df['month_name'] = seasonal_df['month'].apply(lambda x: month_names[int(x)-1])
            
            fig = px.bar(
                seasonal_df,
                x='month_name',
                y='unique_songs',
                labels={'unique_songs': 'Unique Songs', 'month_name': 'Month'},
                title='Unique Songs by Month',
                color='unique_songs',
                color_continuous_scale='Greens'
            )
            st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()

