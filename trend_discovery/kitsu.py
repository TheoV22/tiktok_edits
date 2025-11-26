import requests
from typing import List, Dict
from trend_discovery.utils import _match_anime_to_song

async def _try_kitsu_trending(count: int) -> List[Dict]:
    """
    Get trending anime from Kitsu REST API and pair with genre-matched phonk songs.
    No API key needed!
    """
    try:
        # Kitsu trending anime endpoint
        response = requests.get(
            'https://kitsu.io/api/edge/trending/anime',
            params={'limit': count},
            timeout=15
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        anime_list = data.get('data', [])
        
        # Generate videos with genre-matched songs
        videos = []
        for anime in anime_list[:count]:
            attributes = anime.get('attributes', {})
            anime_title = attributes.get('titles', {}).get('en') or attributes.get('canonicalTitle', 'Unknown Anime')
            
            # Kitsu doesn't directly provide genres in trending endpoint, use title for matching
            song = _match_anime_to_song([], anime_title)
            
            # Calculate trending score from user count and rating
            user_count = attributes.get('userCount', 0)
            trending_score = min(1.0, user_count / 50000) if user_count else 0.65
            
            metadata = {
                "video_id": f"kitsu_{anime.get('id', 0)}",
                "video_url": song['url'],
                "sound_id": song['id'],
                "sound_title": song['title'],
                "sound_author": song['author'],
                "caption": f"{anime_title} edit - {song['title']}",
                "play_url": "",
                "source": "kitsu",
                "trending_score": trending_score
            }
            videos.append(metadata)
        
        return videos
        
    except Exception as e:
        print(f"    Kitsu error: {e}")
        return []
