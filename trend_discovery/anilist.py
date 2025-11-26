import requests
from typing import List, Dict
from datetime import datetime
from trend_discovery.utils import _match_anime_to_song

async def get_anilist_trending_split(airing_count=5, finished_count=5) -> List[Dict]:
    """
    Get trending anime split between airing and finished.
    
    Args:
        airing_count: Number of currently airing anime
        finished_count: Number of recently finished anime
    
    Returns:
        List of anime dicts with title, genres, popularity
    """
    try:
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Determine current season
        if current_month in [1, 2, 3]:
            season = "WINTER"
        elif current_month in [4, 5, 6]:
            season = "SPRING"
        elif current_month in [7, 8, 9]:
            season = "SUMMER"
        else:
            season = "FALL"
        
        # Query 1: Airing anime (current season)
        airing_query = '''
        query ($page: Int, $perPage: Int, $season: MediaSeason, $year: Int) {
            Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: TRENDING_DESC, status: RELEASING, season: $season, seasonYear: $year) {
                    id
                    title { romaji english }
                    genres
                    popularity
                    averageScore
                }
            }
        }
        '''
        
        airing_response = requests.post(
            'https://graphql.anilist.co',
            json={
                'query': airing_query,
                'variables': {
                    'page': 1,
                    'perPage': airing_count,
                    'season': season,
                    'year': current_year
                }
            },
            timeout=15
        )
        
        # Query 2: Recently finished anime
        finished_query = '''
        query ($page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: TRENDING_DESC, status: FINISHED) {
                    id
                    title { romaji english }
                    genres
                    popularity
                    averageScore
                }
            }
        }
        '''
        
        finished_response = requests.post(
            'https://graphql.anilist.co',
            json={
                'query': finished_query,
                'variables': {
                    'page': 1,
                    'perPage': finished_count
                }
            },
            timeout=15
        )
        
        # Merge results
        anime_list = []
        
        if airing_response.status_code == 200:
            airing_data = airing_response.json()
            airing_anime = airing_data.get('data', {}).get('Page', {}).get('media', [])
            for anime in airing_anime:
                title = anime.get('title', {}).get('english') or anime.get('title', {}).get('romaji', 'Unknown')
                anime_list.append({
                    'id': anime.get('id'),
                    'title': title,
                    'genres': anime.get('genres', []),
                    'popularity': anime.get('popularity', 0),
                    'status': 'airing',
                    'source': 'anilist'
                })
        
        if finished_response.status_code == 200:
            finished_data = finished_response.json()
            finished_anime = finished_data.get('data', {}).get('Page', {}).get('media', [])
            for anime in finished_anime:
                title = anime.get('title', {}).get('english') or anime.get('title', {}).get('romaji', 'Unknown')
                anime_list.append({
                    'id': anime.get('id'),
                    'title': title,
                    'genres': anime.get('genres', []),
                    'popularity': anime.get('popularity', 0),
                    'status': 'finished',
                    'source': 'anilist'
                })
        
        return anime_list
        
    except Exception as e:
        print(f"    AniList error: {e}")
        return []


async def _try_anilist_trending(count: int) -> List[Dict]:
    """
    Get trending anime from AniList GraphQL API and pair with genre-matched phonk songs.
    No API key needed! Rate limit: 90 requests/minute.
    """
    try:
        # AniList GraphQL query for trending anime
        query = '''
        query ($page: Int, $perPage: Int) {
            Page(page: $page, perPage: $perPage) {
                media(type: ANIME, sort: TRENDING_DESC) {
                    id
                    title {
                        romaji
                        english
                    }
                    genres
                    popularity
                    averageScore
                }
            }
        }
        '''
        
        variables = {
            'page': 1,
            'perPage': count
        }
        
        response = requests.post(
            'https://graphql.anilist.co',
            json={'query': query, 'variables': variables},
            timeout=15
        )
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        anime_list = data.get('data', {}).get('Page', {}).get('media', [])
        
        # Generate videos with genre-matched songs
        videos = []
        for anime in anime_list[:count]:
            anime_title = anime.get('title', {}).get('english') or anime.get('title', {}).get('romaji', 'Unknown Anime')
            genres = anime.get('genres', [])
            popularity = anime.get('popularity', 0)
            
            # Match anime genre to song
            song = _match_anime_to_song(genres, anime_title)
            
            # Calculate trending score from popularity
            # AniList popularity ranges from 1000s to 100000+
            trending_score = min(1.0, popularity / 100000) if popularity else 0.7
            
            metadata = {
                "video_id": f"ani list_{anime.get('id', 0)}",
                "video_url": song['url'],
                "sound_id": song['id'],
                "sound_title": song['title'],
                "sound_author": song['author'],
                "caption": f"{anime_title} edit - {song['title']}",
                "play_url": "",
                "source": "anilist",
                "trending_score": trending_score,
                "anime_genres": genres  # Extra metadata
            }
            videos.append(metadata)
        
        return videos
        
    except Exception as e:
        print(f"    AniList error: {e}")
        return []
