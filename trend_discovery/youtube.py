import subprocess
import json
import asyncio
from typing import List, Dict
from trend_discovery.utils import _enhanced_song_extraction, _calculate_trending_score, _extract_hashtags

async def search_shorts_for_anime(anime_title: str, count=3) -> List[Dict]:
    """
    Search YouTube Shorts for a specific anime.
    
    Uses multiple query variations and enhanced metadata extraction.
    """
    try:
        # Try multiple search queries
        queries = [
            f'{anime_title} edit phonk shorts',
            f'{anime_title} amv shorts',
            f'{anime_title} edit 4k shorts'
        ]
        
        all_shorts = []
        seen_ids = set()
        
        for query in queries:
            search_query = f"ytsearch{count}:{query}"
            
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                "--skip-download",
                search_query
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                continue
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    
                    video_id = data.get('id', '')
                    if video_id in seen_ids:
                        continue
                    seen_ids.add(video_id)
                    
                    # Filter for Shorts (< 60s) and minimum views
                    duration = data.get('duration') or 0
                    view_count = data.get('view_count') or 0
                    
                    if duration <= 0 or duration >= 60:
                        continue
                    if view_count < 10000:  # Minimum 10K views
                        continue
                    
                    title = data.get('title', 'Unknown')
                    description = data.get('description', '')
                    uploader = data.get('uploader', data.get('channel', 'Unknown'))
                    like_count = data.get('like_count') or 0
                    upload_date = data.get('upload_date', '')
                    
                    # Enhanced song extraction
                    sound_title, sound_author = _enhanced_song_extraction(title, description)
                    
                    # Calculate trending score
                    trending_score = _calculate_trending_score(
                        view_count, like_count, upload_date, duration
                    )
                    
                    metadata = {
                        "video_id": video_id,
                        "video_url": f"https://www.youtube.com/watch?v={video_id}",
                        "sound_id": video_id,
                        "sound_title": sound_title,
                        "sound_author": sound_author,
                        "caption": title,
                        "anime_title": anime_title,  # Track which anime this is for
                        "duration": duration,
                        "view_count": view_count,
                        "like_count": like_count,
                        "upload_date": upload_date,
                        "channel_name": uploader,
                        "source": "youtube_shorts",
                        "trending_score": trending_score
                    }
                    all_shorts.append(metadata)
                    
                    if len(all_shorts) >= count:
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            if len(all_shorts) >= count:
                break
        
        return all_shorts[:count]
        
    except Exception as e:
        print(f"    Error searching shorts for {anime_title}: {e}")
        return []


async def _try_youtube_shorts_scrape(count: int, max_retries: int = 3) -> List[Dict]:
    """
    Enhanced YouTube Shorts scraping with comprehensive metadata extraction.
    """
    for attempt in range(max_retries):
        try:
            # Search for more videos than needed to allow filtering
            search_query = f"ytsearch{count * 3}:anime edit shorts"
            
            # Use yt-dlp to get full metadata (not flat-playlist for more data)
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                "--skip-download",
                search_query
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return []
            
            # Parse JSON lines output
            videos = []
            seen_ids = set()
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    
                    # Extract basic metadata
                    video_id = data.get('id', '')
                    if video_id in seen_ids:
                        continue
                    seen_ids.add(video_id)
                    
                    # Get duration and filter for Shorts (< 60s)
                    duration = data.get('duration', 0)
                    if duration <= 0 or duration >= 60:
                        continue  # Skip non-Shorts or invalid duration
                    
                    title = data.get('title', 'Unknown')
                    description = data.get('description', '')
                    uploader = data.get('uploader', data.get('channel', 'Unknown'))
                    view_count = data.get('view_count', 0)
                    like_count = data.get('like_count', 0)
                    upload_date = data.get('upload_date', '')  # YYYYMMDD format
                    
                    # Extract hashtags from title and description
                    hashtags = _extract_hashtags(title + ' ' + description)
                    
                    # Enhanced song extraction (tries title first, then description)
                    sound_title, sound_author = _enhanced_song_extraction(title, description)
                    
                    # Calculate improved trending score
                    trending_score = _calculate_trending_score(
                        view_count, like_count, upload_date, duration
                    )
                    
                    metadata = {
                        "video_id": video_id,
                        "video_url": f"https://www.youtube.com/watch?v={video_id}",
                        "sound_id": video_id,
                        "sound_title": sound_title,
                        "sound_author": sound_author,
                        "caption": title,
                        "duration": duration,
                        "view_count": view_count,
                        "like_count": like_count,
                        "upload_date": upload_date,
                        "channel_name": uploader,
                        "hashtags": hashtags,
                        "play_url": "",
                        "source": "youtube_scrape",
                        "trending_score": trending_score
                    }
                    videos.append(metadata)
                    
                    if len(videos) >= count:
                        break
                        
                except json.JSONDecodeError:
                    continue
            
            # Sort by trending score (highest first)
            videos.sort(key=lambda x: x['trending_score'], reverse=True)
            return videos[:count]
            
        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            print("    YouTube scraping timed out after retries")
            return []
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            print(f"    YouTube scraping error: {e}")
            return []
    
    return []
