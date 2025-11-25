import asyncio
from TikTokApi import TikTokApi
import os
import json

async def get_trending_anime_edits(hashtag: str = "animeedit", count: int = 5):
    """
    Searches for trending videos with the given hashtag.
    Returns a list of dictionaries with video metadata.
    """
    videos = []
    try:
        async with TikTokApi() as api:
            await api.create_sessions(ms_tokens=[os.environ.get("MS_TOKEN")], num_sessions=1, sleep_after=3)
            tag = api.hashtag(name=hashtag)
            async for video in tag.videos(count=count):
                video_data = video.as_dict
                music = video_data.get("music", {})
                
                # Extract relevant info
                info = {
                    "video_id": video_data.get("id"),
                    "video_url": f"https://www.tiktok.com/@{video_data.get('author', {}).get('uniqueId')}/video/{video_data.get('id')}",
                    "sound_id": music.get("id"),
                    "sound_title": music.get("title"),
                    "sound_author": music.get("authorName"),
                    "caption": video_data.get("desc", ""),
                    "play_url": music.get("playUrl") # This might be empty or restricted
                }
                videos.append(info)
                
    except Exception as e:
        print(f"Error scraping TikTok: {e}")
        # Fallback or empty list
        return []

    return videos

if __name__ == "__main__":
    # Simple test
    asyncio.run(get_trending_anime_edits())
