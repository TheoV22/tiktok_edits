import imageio_ffmpeg
import os
import subprocess
import glob
import requests
import asyncio
from typing import List

async def get_high_quality_clips(
    anime_title: str,
    count: int = 5,
    sources: List[str] = ['sakugabooru', 'youtube_hq', 'youtube_shorts'],
    output_dir: str = "output/clips"
) -> List[str]:
    """
    Get high-quality clips from multiple sources (priority order).
    """
    os.makedirs(output_dir, exist_ok=True)
    all_clips = []
    
    for source in sources:
        if len(all_clips) >= count:
            break
            
        remaining = count - len(all_clips)
        print(f"  → Gathering clips from {source} (need {remaining})...")
        
        if source == 'sakugabooru':
            clips = await get_clips_from_sakugabooru(anime_title, remaining, output_dir)
            all_clips.extend(clips)
            
        elif source == 'youtube_hq':
            clips = await get_clips_from_youtube_hq(anime_title, remaining, output_dir)
            all_clips.extend(clips)
            
        elif source == 'youtube_shorts':
            # Fallback to standard search
            clips = get_anime_clips(f"{anime_title} edit clips", remaining, output_dir)
            all_clips.extend(clips)
            
    return all_clips[:count]


async def get_clips_from_sakugabooru(anime_title: str, count: int, output_dir: str) -> List[str]:
    """
    Search Sakugabooru API for high-quality animation cuts.
    """
    try:
        # Clean title for tags (replace spaces with underscores)
        tag = anime_title.lower().replace(' ', '_')
        # Remove special chars
        tag = "".join(c for c in tag if c.isalnum() or c == '_')
        
        url = "https://sakugabooru.com/post.json"
        params = {
            "tags": f"{tag} order:score",
            "limit": count * 2  # Fetch more to filter
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return []
            
        posts = response.json()
        downloaded_clips = []
        
        for post in posts:
            if len(downloaded_clips) >= count:
                break
                
            file_url = post.get('file_url')
            if not file_url or not file_url.endswith('.mp4'):
                continue
                
            # Download file
            filename = f"sakuga_{post.get('id')}.mp4"
            filepath = os.path.join(output_dir, filename)
            
            if not os.path.exists(filepath):
                try:
                    # Download using requests
                    r = requests.get(file_url, stream=True, timeout=20)
                    if r.status_code == 200:
                        with open(filepath, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                        downloaded_clips.append(filepath)
                except Exception as e:
                    print(f"    Failed to download sakuga clip: {e}")
                    continue
            else:
                downloaded_clips.append(filepath)
                
        return downloaded_clips
        
    except Exception as e:
        print(f"    Sakugabooru error: {e}")
        return []


async def get_clips_from_youtube_hq(anime_title: str, count: int, output_dir: str) -> List[str]:
    """
    Search YouTube for high-quality clips (no watermark, 4k).
    """
    queries = [
        f"{anime_title} twixtor no watermark",
        f"{anime_title} clips 4k",
        f"{anime_title} raw scenes"
    ]
    
    downloaded_clips = []
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    for query in queries:
        if len(downloaded_clips) >= count:
            break
            
        search_query = f"ytsearch{count}:{query}"
        output_template = os.path.join(output_dir, "hq_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--ffmpeg-location", ffmpeg_exe,
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--max-filesize", "50M",
            "--match-filter", "duration > 5 & duration < 45",  # Short clips only
            "-o", output_template,
            search_query
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Find new files
            files = glob.glob(os.path.join(output_dir, "hq_*.mp4"))
            # Filter valid ones
            for f in files:
                if f not in downloaded_clips:
                    downloaded_clips.append(f)
                    
        except Exception as e:
            print(f"    YouTube HQ error: {e}")
            continue
            
    return downloaded_clips


def get_anime_clips(query: str, count: int = 3, output_dir: str = "output/clips") -> List[str]:
    """
    Legacy/Fallback: Searches for and downloads anime clips from YouTube using yt-dlp.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    search_query = f"ytsearch{count}:{query}"
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--ffmpeg-location", ffmpeg_exe,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--max-filesize", "50M",
        "-o", output_template,
        search_query
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        files = glob.glob(os.path.join(output_dir, "*"))
        valid_extensions = {'.mp4', '.mkv', '.webm', '.mov'}
        video_files = [f for f in files if os.path.splitext(f)[1].lower() in valid_extensions and not f.endswith('.part') and 'sakuga_' not in f and 'hq_' not in f]
        return video_files[:count]
    except subprocess.CalledProcessError as e:
        print(f"Error gathering clips: {e}")
        return []
