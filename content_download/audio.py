import os
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import shutil
import dotenv

def get_spotify_client():
    """
    Initializes and returns a Spotipy client using environment variables.
    Requires SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET to be set.
    """
    dotenv.load_dotenv()
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET environment variables must be set.")
        
    auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth_manager)

def get_top_tracks_by_genre(genre: str, limit: int = 5):
    """
    Searches for the top tracks of a given genre on Spotify.
    """
    sp = get_spotify_client()
    
    # Search for tracks with the genre
    # Query format: "genre:phonk"
    query = f"genre:{genre}"
    results = sp.search(q=query, type='track', limit=limit)
    
    tracks = []
    if results and 'tracks' in results and 'items' in results['tracks']:
        for item in results['tracks']['items']:
            track_info = {
                'name': item['name'],
                'artist': item['artists'][0]['name'],
                'url': item['external_urls']['spotify']
            }
            tracks.append(track_info)
            
    return tracks

def download_tracks(track_urls: list, output_dir: str):
    """
    Downloads tracks using spotdl.
    """
    if not track_urls:
        print("No tracks to download.")
        return []

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    downloaded_files = []
    
    # Check if spotdl is installed
    if shutil.which("spotdl") is None:
        raise RuntimeError("spotdl is not installed or not in PATH. Please install it with 'pip install spotdl'.")

    # Change to output directory to have spotdl download there
    # or use --output argument if supported nicely, but cd is safer for simple usage
    current_dir = os.getcwd()
    try:
        os.chdir(output_dir)
        cmd = ["spotdl", "download"] + track_urls
        subprocess.run(cmd, check=True)
        
        # Collect downloaded files (spotdl downloads as mp3 by default usually)
        for file in os.listdir("."):
             if file.endswith(".mp3"): # capable of improvement to match exactly what was downloaded
                 downloaded_files.append(os.path.abspath(file))
                 
    except subprocess.CalledProcessError as e:
        print(f"Error downloading tracks: {e}")
    finally:
        os.chdir(current_dir)
        
    return downloaded_files

def download_genre_tracks(genre: str, output_dir: str, limit: int = 5):
    """
    Main function to get top tracks for a genre and download them.
    """
    print(f"Searching for top {limit} {genre} tracks...")
    tracks = get_top_tracks_by_genre(genre, limit)
    
    if not tracks:
        print(f"No tracks found for genre: {genre}")
        return []
        
    print(f"Found {len(tracks)} tracks:")
    urls = []
    for t in tracks:
        print(f"- {t['name']} by {t['artist']}")
        urls.append(t['url'])
        
    print("Downloading tracks...")
    downloaded = download_tracks(urls, output_dir)
    print(f"Downloaded {len(downloaded)} tracks to {output_dir}")
    return downloaded

