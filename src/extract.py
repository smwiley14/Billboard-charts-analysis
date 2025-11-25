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



load_dotenv()

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
        
    def get_access_token(self) -> str:
        response = requests.post(
            self.token_url,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret)
        )

        return response.json()["access_token"]

    def make_request(self, endpoint, params=None, body=None):
        
        url = f"{self.base_url}/{endpoint}"
        if params:
            for param in params:
                url+=f"?{param}"
        access_token = self.get_access_token()
        res = requests.get(
            url,
            headers={
                "Authorization" : f"Bearer {access_token}"
            }
        )

        if res.status_code == 200:
            return res.json()
        else:
            print(f"Failed to fetch: {res.status_code}")


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
    
    

    def get_mbid(self, link):
        endpoint = f"url?resource={link}&inc=artist-rels"
        res = self.make_request(endpoint)

        if not res:
            return None

        relations = res.get("relations", [])
        if not relations:
            return None

        # Safely navigate nested objects
        artist = relations[0].get("artist", {})
        return artist.get("id")
    
    
    def mb_get_artist_tag(self, id):
        endpoint = f"artist/{id}?inc=tags"
        tags = self.make_request(endpoint)['tags']
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

    def get_recco_song_details(self, ids):
        ids_string=','.join(ids)
        res = requests.get(f"{self.base}/track?ids={ids_string}", headers=self.headers)
        if(res.status_code == 200):
            return res.json()['content']
        else:
            print(f"request failed with code {res.status_code} due to {res.reason}")
            return None

    def get_recco_audio_analysis(self, id):
        res = requests.get(f"{self.base}/track/{id}/audio-features", headers=self.headers)
        if(res.status_code == 200):
            return res.json()
        else:
            print(f"{id}")
            print(f"audio request failed with code {res.status_code} due to {res.reason}")

    def get_recco_artist_details(self, id):
        res = requests.get(f"{base_self.baserecco}/artist/{id}", headers=self.headers)
        return res.json()
