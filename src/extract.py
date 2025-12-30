import os
from dotenv import load_dotenv
import requests
import base64 
import json
from urllib.parse import quote
import time
import pandas as pd
import billboard
from billboard import ChartData
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import create_engine, text



# load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
base_url = "https://api.spotify.com/v1"
redirect_uri = os.getenv("REDIRECT_URI")
scope = "playlist-read-public"
token_url = "https://accounts.spotify.com/api/token"

class SpotifyAPI:
    def __init__(self) -> object:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.token_url = token_url
        
    def get_access_token(self, max_retries=3, initial_delay=1):
        """
        Get Spotify access token with retry logic for JSON decode errors.
        """
        for attempt in range(1, max_retries + 1):
            try:
                if hasattr(self, "_token") and time.time() < self._token_expires_at:
                    return self._token

                response = requests.post(
                    self.token_url,
                    data={"grant_type": "client_credentials"},
                    auth=(self.client_id, self.client_secret),
                    timeout=10
                )
                
                if response.status_code == 200:
                    try:
                        return response.json()["access_token"]
                    except (ValueError, KeyError) as e:
                        if attempt < max_retries:
                            delay = initial_delay * (2 ** (attempt - 1))
                            print(f"Error parsing access token response: {e}. Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                            time.sleep(delay)
                            continue
                        else:
                            print(f"Error parsing access token response after {max_retries} attempts: {e}")
                            raise
                else:
                    if attempt < max_retries:
                        delay = initial_delay * (2 ** (attempt - 1))
                        print(f"Failed to get access token: HTTP {response.status_code}. Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Failed to get access token after {max_retries} attempts: HTTP {response.status_code}")
                        raise Exception(f"Failed to get access token: HTTP {response.status_code}")
                        
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries:
                    delay = initial_delay * (2 ** (attempt - 1))
                    print(f"Network error getting access token: {e}. Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"Network error getting access token after {max_retries} attempts: {e}")
                    raise
        
        raise Exception("Failed to get access token after all retries")

    def make_request(self, endpoint, params=None, body=None, max_retries=3, initial_delay=1):
        """
        Make a request to Spotify API with retry logic for JSON decode errors and rate limits.
        """
        url = f"{self.base_url}/{endpoint}"
        if params:
            for param in params:
                url+=f"?{param}"
        
        for attempt in range(1, max_retries + 1):
            try:
                access_token = self.get_access_token()
                res = requests.get(
                    url,
                    headers={
                        "Authorization" : f"Bearer {access_token}"
                    },
                    timeout=30
                )

                # Handle rate limiting (429)
                if res.status_code == 429:
                    if attempt < max_retries:
                        # Check for Retry-After header
                        retry_after = res.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = int(retry_after) + 1
                            except ValueError:
                                delay = initial_delay * (2 ** (attempt - 1))
                        else:
                            delay = initial_delay * (2 ** (attempt - 1))
                        delay = min(delay, 60)  # Cap at 60 seconds
                        print(f"Rate limited (429). Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Rate limited (429). Max retries ({max_retries}) exceeded.")
                        return None

                if res.status_code == 200:
                    try:
                        return res.json()
                    except (ValueError, requests.exceptions.JSONDecodeError) as e:
                        if attempt < max_retries:
                            delay = initial_delay * (2 ** (attempt - 1))
                            print(f"JSON decode error: {e}. Response text: {res.text[:100]}. Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                            time.sleep(delay)
                            continue
                        else:
                            print(f"JSON decode error after {max_retries} attempts: {e}. Response text: {res.text[:200]}")
                            return None
                else:
                    if attempt < max_retries and res.status_code >= 500:
                        # Retry on server errors
                        delay = initial_delay * (2 ** (attempt - 1))
                        print(f"Server error {res.status_code}. Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Failed to fetch: {res.status_code} - {res.reason}")
                        return None
                        
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries:
                    delay = initial_delay * (2 ** (attempt - 1))
                    print(f"Network error: {e}. Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"Network error after {max_retries} attempts: {e}")
                    return None
        
        return None


    def get_categories(self, country="US", limit=2):
        return self.make_request(f"browse/categories?country={country}&limit={limit}")

    def get_playlists(self, category_id, country="US", limit=5):
        return self.make_request(f"search?q=category:{category_id}&type=playlist&limit={limit}")

    def search_song(self, song, artist):
        query = f"track:{song} artist:{artist}"
        endpoint = f"search?q={quote(query)}&type=track&limit=1"
        res = self.make_request(endpoint=endpoint)
        if not res:
            return None

        tracks = res.get("tracks", [])
        if not tracks:
            return None
 
        if tracks['total'] == 0:
            return -1
        id = self.make_request(endpoint=endpoint)['tracks']['items'][0]
        # print(id)
        return id
    def search_artist(self, artist):
        query = f"artist:{artist}"
        endpoint = f"search?q={quote(query)}&type=artist&limit=1"
        id = self.make_request(endpoint=endpoint)
        
        # return self.make_request(f"tracks/{id}")
        return id   
    def get_artist(self, id):
        return self.make_request(f"artists/{id}")
    



# base_url_last_fm="https://ws.audioscrobbler.com/2.0"
# last_fm_api_key = os.getenv("LAST_FM_API_KEY")
# last_fm_shared_secret = os.getenv("LAST_FM_SHARED_SECRET")
base = f"https://musicbrainz.org/ws/2"

session = requests.Session()

retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    raise_on_status=False,
)

session.mount("https://", HTTPAdapter(max_retries=retries))



#Music Brainz API
class MusicBrainzAPI():
    def __init__(self) -> object:
        self.base = base
        self.session = requests.Session()
        self._db_engine = None
    
    def _get_db_engine(self):
        """Get or create database engine connection."""
        if self._db_engine is None:
            database_url = os.getenv("MUSIC_WAREHOUSE_DATABASE_URL")
            if not database_url:
                return None
            
            # Ensure we're using psycopg2 driver
            if not database_url.startswith("postgresql"):
                return None
            
            if "+psycopg2" not in database_url:
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
            
            self._db_engine = create_engine(
                database_url,
                pool_pre_ping=True,
                echo=False
            )
        return self._db_engine
    
    def _artist_has_mbid_and_tag(self, artist_id):
        """Check if an artist already has mbid and tag in the database."""
        if not artist_id:
            return False, None, None
        
        engine = self._get_db_engine()
        if not engine:
            # If no database connection, assume artist doesn't have data and proceed
            return False, None, None
        
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT mbid, tag FROM artists WHERE artist_id = :artist_id LIMIT 1"),
                    {"artist_id": artist_id}
                )
                row = result.fetchone()
                if row and row[0] and row[1]:  # Both mbid and tag exist
                    return True, row[0], row[1]
                elif row and row[0]:  # Only mbid exists
                    return False, row[0], None
                else:
                    return False, None, None
        except Exception as e:
            print(f"Error checking if artist has mbid and tag in database: {e}")
            # On error, assume artist doesn't have data and proceed
            return False, None, None

        
    # def make_request(self, endpoint):
    #     url = f"{base_url_last_fm}/{endpoint}&api_key={last_fm_api_key}&format=json"
    #     res = requests.get(url)
    #     print(url)
    #     return res.json()
    
    def make_request(self, endpoint, retries=3):
        url = f"{self.base}/{endpoint}&fmt=json"
        print(url)

        for attempt in range(1, retries + 1):
            try:
                res = self.session.get(url, timeout=20)

                # Handle rate limiting
                if res.status_code == 503:
                    wait = 1 * attempt
                    print(f"Rate limit hit. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                if res.status_code != 200:
                    print(f"HTTP {res.status_code}: {res.reason}")
                    return None

                try:
                    return res.json()
                except ValueError:
                    print("Error decoding JSON")
                    return None

            except (requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError) as e:
                print(f"Network error: {e}. Attempt {attempt}/{retries}")
                time.sleep(1)
        
        print("Max retries exceeded.")
        return None
    
    

    def get_mbid(self, link, artist_id=None):
        """
        Get MusicBrainz ID from a Spotify URL.
        
        Args:
            link: Spotify artist URL
            artist_id: Spotify artist_id to check in database (optional)
        
        Returns:
            MusicBrainz ID if fetched or found in DB, None on error
        """
        # Check database first if artist_id is provided
        if artist_id:
            has_data, existing_mbid, existing_tag = self._artist_has_mbid_and_tag(artist_id)
            if has_data:
                print(f"Artist {artist_id} already has mbid ({existing_mbid}) and tag ({existing_tag}) in database, skipping MusicBrainz API calls")
                return existing_mbid  # Return existing mbid so it can be used
            elif existing_mbid:
                # Artist has mbid but no tag, return the existing mbid
                print(f"Artist {artist_id} already has mbid ({existing_mbid}) in database, skipping get_mbid call")
                return existing_mbid
        
        endpoint = f"url?resource={link}&inc=artist-rels"
        res = self.make_request(endpoint)

        if not res:
            return None

        relations = res.get("relations", [])
        if not relations:
            return None

        artist = relations[0].get("artist", {})
        return artist.get("id")
    
    
    def mb_get_artist_tag(self, id, artist_id=None):
        """
        Get artist tag/genre from MusicBrainz ID.
        
        Args:
            id: MusicBrainz artist ID
            artist_id: Spotify artist_id to check in database (optional)
        
        Returns:
            Artist tag if fetched, None if artist already has tag in DB or on error
        """
        # Check database first if artist_id is provided
        if artist_id:
            has_data, existing_mbid, existing_tag = self._artist_has_mbid_and_tag(artist_id)
            if has_data:
                print(f"Artist {artist_id} already has tag ({existing_tag}) in database, skipping MusicBrainz tag fetch")
                return existing_tag
        
        endpoint = f"artist/{id}?inc=tags"
        res = self.make_request(endpoint)
        if not res:
            return None
        tags = res.get('tags', [])
        if not tags:
            return None
        top = max(tags, key=lambda tag: tag.get('count')).get('name', "")
        return top



class BillBoardChart:
    def __init__(self, date):
        self.data = billboard.ChartData('hot-100', date=date)




base_recco="https://api.reccobeats.com/v1"
headers = {
  'Accept': 'application/json'
}


class ReccoBeats:
    def __init__(self):
        self.base=base_recco
        self.headers=headers
        self._db_engine = None
    
    def _get_db_engine(self):
        """Get or create database engine connection."""
        if self._db_engine is None:
            database_url = os.getenv("MUSIC_WAREHOUSE_DATABASE_URL")
            if not database_url:
                return None
            
            # Ensure we're using psycopg2 driver
            if not database_url.startswith("postgresql"):
                return None
            
            if "+psycopg2" not in database_url:
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://")
            
            self._db_engine = create_engine(
                database_url,
                pool_pre_ping=True,
                echo=False
            )
        return self._db_engine
    
    def _song_exists_in_db(self, song_id):
        """Check if a song already exists in the database."""
        if not song_id:
            return False
        
        engine = self._get_db_engine()
        if not engine:
            # If no database connection, assume song doesn't exist and proceed
            return False
        
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM songs WHERE song_id = :song_id LIMIT 1"),
                    {"song_id": song_id}
                )
                return result.fetchone() is not None
        except Exception as e:
            print(f"Error checking if song exists in database: {e}")
            # On error, assume song doesn't exist and proceed
            return False
    
    def _artist_exists_in_db(self, artist_id):
        """Check if an artist already exists in the database."""
        if not artist_id:
            return False
        
        engine = self._get_db_engine()
        if not engine:
            # If no database connection, assume artist doesn't exist and proceed
            return False
        
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM artists WHERE artist_id = :artist_id LIMIT 1"),
                    {"artist_id": artist_id}
                )
                return result.fetchone() is not None
        except Exception as e:
            print(f"Error checking if artist exists in database: {e}")
            # On error, assume artist doesn't exist and proceed
            return False

    def _make_request_with_retry(self, url, max_retries=5, initial_delay=1):
        ## Make a request with exponential backoff retry logic for rate limiting.
 
        for attempt in range(1, max_retries + 1):
            try:
                res = requests.get(url, headers=self.headers, timeout=30)
                
                if res.status_code == 200:
                    return res
                
                if res.status_code == 429:
                    if attempt < max_retries:
                        delay = initial_delay * (2 ** (attempt - 1))
                        # Cap at 60 seconds
                        delay = min(delay, 60)
                        
                        retry_after = res.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = int(retry_after) + 1  
                            except ValueError:
                                pass
                        
                        print(f"Rate limited (429). Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Rate limited (429). Max retries ({max_retries}) exceeded.")
                        return res
                
                # Dont retry if other errors
                print(f"Request failed with code {res.status_code}: {res.reason}")
                return res
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < max_retries:
                    delay = initial_delay * (2 ** (attempt - 1))
                    print(f"Network error: {e}. Retrying in {delay}s (attempt {attempt}/{max_retries})...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"Network error after {max_retries} attempts: {e}")
                    return None
        
        return None

    def get_recco_song_details(self, ids):
        ids_string=','.join(ids)
        url = f"{self.base}/track?ids={ids_string}"
        res = self._make_request_with_retry(url)
        
        if res and res.status_code == 200:
            try:
                return res.json()['content']
            except (KeyError, ValueError) as e:
                print(f"Error parsing response: {e}")
                return None
        else:
            return None

    def get_recco_audio_analysis(self, id, song_id=None):
        """
        Get audio analysis for a track.
        
        Args:
            id: ReccoBeats track ID
            song_id: Spotify song_id to check in database (optional)
        
        Returns:
            Audio features dict if fetched, None if song already exists in DB or on error
        """
        # Check database first if song_id is provided
        if song_id and self._song_exists_in_db(song_id):
            print(f"Song {song_id} already exists in database, skipping audio features fetch")
            return None
        
        url = f"{self.base}/track/{id}/audio-features"
        res = self._make_request_with_retry(url)
        
        if res and res.status_code == 200:
            try:
                return res.json()
            except ValueError as e:
                print(f"Error parsing audio analysis response for {id}: {e}")
                return None
        else:
            if res:
                print(f"Audio analysis request failed for {id} with code {res.status_code}: {res.reason}")
            return None

    def get_recco_artist_details(self, id, artist_id=None):
        """
        Get artist details from ReccoBeats API.
        
        Args:
            id: ReccoBeats artist ID
            artist_id: Spotify artist_id to check in database (optional)
        
        Returns:
            Artist details dict if fetched, None if artist already exists in DB or on error
        """
        # Check database first if artist_id is provided
        if artist_id and self._artist_exists_in_db(artist_id):
            print(f"Artist {artist_id} already exists in database, skipping artist details fetch")
            return None
        
        url = f"{self.base}/artist/{id}"
        res = self._make_request_with_retry(url)
        if res and res.status_code == 200:
            return res.json()
        return None