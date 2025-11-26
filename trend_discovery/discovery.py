"""
Multi-source trending anime edits discovery system.
Tries multiple sources in priority order:
1. YouTube Shorts scraping (no API key needed)
2. AniList GraphQL API (trending anime with genre-matched songs)
3. Kitsu REST API (trending anime fallback)
4. Jikan/MyAnimeList (final fallback)
5. Hardcoded popular tracks
"""

import asyncio
import os
import requests
from typing import List, Dict, Optional

from content_download.clips import get_high_quality_clips
from content_download.audio import download_audio

from trend_discovery.anilist import get_anilist_trending_split, _try_anilist_trending
from trend_discovery.kitsu import _try_kitsu_trending
from trend_discovery.youtube import search_shorts_for_anime, _try_youtube_shorts_scrape
from trend_discovery.scoring import score_shorts, select_diverse_content
from trend_discovery.utils import _get_popular_phonk_songs, _get_hardcoded_tracks

# ============================================================================
# DATA-DRIVEN TRENDING DISCOVERY SYSTEM
# ============================================================================

async def get_trending_anime_edits_v2(count=3, temperature=0.5) -> Dict:
    """
    Data-driven workflow: 
    AniList anime → YouTube Shorts → Scoring → Selection → Audio Download → Clip Gathering
    
    Args:
        count: Number of final edits to return (not used in new system)
        temperature: 0-1, controls diversity (affects anime selection count)
    
    Returns:
        Dict with selected_animes, song, audio_path, clip_paths, metadata
    """
    print(f"🔍 Data-Driven Discovery (temp={temperature:.2f})...")
    
    # Step 1: Get 10 trending anime (5 airing + 5 finished)
    print("\n[Step 1] Getting trending anime from AniList...")
    anime_list = await get_anilist_trending_split(airing_count=5, finished_count=5)
    
    if not anime_list:
        print("  ✗ AniList failed, trying Kitsu...")
        anime_list = await _try_kitsu_trending(10)
    
    if not anime_list:
        print("  ✗ All anime sources failed")
        return None
    
    print(f"  ✓ Got {len(anime_list)} trending anime")
    
    # Step 2: Search YouTube Shorts for each anime (3 shorts each = 30 total)
    print("\n[Step 2] Searching YouTube Shorts for each anime...")
    all_shorts = []
    for anime in anime_list:
        anime_title = anime.get('title', anime.get('caption', 'Unknown'))
        print(f"  → Searching shorts for: {anime_title}")
        shorts = await search_shorts_for_anime(anime_title, count=3)
        print(f"    Found {len(shorts)} shorts")
        all_shorts.extend(shorts)
    
    print(f"  ✓ Total shorts found: {len(all_shorts)}")
    
    if not all_shorts:
        print("  ✗ No shorts found")
        return None
    
    # Step 3: Score and select best content
    print("\n[Step 3] Scoring and selecting best shorts...")
    scored_shorts = score_shorts(all_shorts, temperature)
    selected = select_diverse_content(
        scored_shorts,
        temperature=temperature
    )
    
    print(f"  ✓ Selected {len(selected['animes'])} anime(s) + 1 song")
    print(f"    Song: {selected['song']['sound_title']} by {selected['song']['sound_author']}")
    
    # Step 4: Download full song
    print("\n[Step 4] Downloading audio...")
    song_data = selected['song']
    audio_filename = f"{song_data['sound_id']}.mp3"
    audio_path = os.path.join("output/audio", audio_filename)
    
    # Use video_url as source for audio
    downloaded_audio = download_audio(song_data['video_url'], audio_path)
    if not downloaded_audio:
        print("  ✗ Audio download failed")
        return None
    print(f"  ✓ Audio downloaded: {downloaded_audio}")
    
    # Step 5: Download high-quality clips
    print("\n[Step 5] Gathering high-quality clips...")
    clip_paths = []
    for anime_title in selected['animes']:
        print(f"  → Getting clips for: {anime_title}")
        clips = await get_high_quality_clips(
            anime_title,
            count=5,
            sources=['sakugabooru', 'youtube_hq', 'youtube_shorts'],
            output_dir="output/clips"
        )
        clip_paths.extend(clips)
        
    print(f"  ✓ Collected {len(clip_paths)} clips total")
    
    return {
        'selected_animes': selected['animes'],
        'song': selected['song'],
        'audio_path': downloaded_audio,
        'clip_paths': clip_paths,
        'metadata': selected
    }
