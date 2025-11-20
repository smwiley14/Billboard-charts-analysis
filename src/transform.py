from extract import SpotifyAPI, MusicBrainzAPI, ReccoBeats, BillBoardChart
from datetime import date
import re
import unicodedata
import time
from pandas import pd

sp = SpotifyAPI()
mb = MusicBrainzAPI()
rec = ReccoBeats()
def get_spotify_song_ids_and_artists(chart) -> tuple [list, list]:
    artists = []
    song_ids = []
    for song in chart:
        artist = normalize_artist_name(song.artist)
        res = sp.search_song(song.title, artist)
        #if the song is found, add song and artist
        if res and res!= -1:
            song_ids.append(res['id'])
            existing_ids = {a["id"] for a in artists}
            for item in res.get("artists", []):
                artist_id = item.get("id")
                artist_url = item.get("external_urls", {}).get("spotify")
                artist_name = item.get("name")
                if artist_id and artist_id not in existing_ids:
                    artists.append({
                        "name": artist_name,
                        "id": artist_id,
                        "url": artist_url
                    })
                    existing_ids.add(artist_id)
    return (song_ids, pd.DataFrame(artists))


def normalize_artist_name(artist) -> str:
    #special case
    if artist == "JEONGYEON, JIHYO & CHAEYOUNG Of TWICE":
        artist = "TWICE"
    #only need to get one artist if there are multiple

    else:
        for c in ["Featuring", ",", "&", ":"]:
            if c in artist:
                artist = artist.split(c)[0]
    
    return artist
    

def get_tags_music_brainz(artists):
    mbids = []
    for artist in artists:
        url = artist['url']
        # print(url)
        mbid = mb.get_mbid(url)
        if mbid:
            artist['mbid'] = mbid
            tag = mb.mb_get_artist_tag(mbid)
            if tag:
                artist['tag'] = tag
        else:
            print(f"unable to get mbid for {url}")
        time.sleep(1)

def get_audio_details(song_ids):
    BATCH_SIZE = 40
    all_results = []
    for i in range(0, len(song_ids), BATCH_SIZE):
        batch = song_ids[i:i + BATCH_SIZE]
        results=rec.get_recco_song_details(batch)['content']
        for r in results:
            song_id = r['id']
            all_results.append(r)
        time.sleep(1)


    for item in all_results:
        res = rec.get_recco_audio_analysis(item['id'])
        item.update(res)

    audio_features = pd.DataFrame(all_results)
    dropped = ['ean', 'id', 'availableCountries', 'isrc', 'upc', 'href']
    audio_features.drop(labels=dropped, inplace=True,errors='ignore')
    return audio_features

def get_chart_dataframe(chart):
    rows = []
    for entry in chart:
        rows.append({
            "title": entry.title,
            "artist": entry.artist,
            "rank": entry.rank,
            "isNew": entry.isNew,
            "weeks": entry.weeks,
            "peakPos": entry.peakPos
        })

    return pd.DataFrame(rows)

def get_dataframes():
    today = date.today()
    chart = BillBoardChart(today).data

    df_chart = get_chart_dataframe(chart)
    song_ids, df_artists = get_spotify_song_ids_and_artists(chart)
    get_tags_music_brainz(df_artists)
    
    df_audio = get_audio_details(song_ids)

    return {
        "chart": df_chart,
        "audio": df_audio,
        "artists" : df_artists
    }
    # print(song_ids)
if __name__ == "__main__":
    get_dataframes()



