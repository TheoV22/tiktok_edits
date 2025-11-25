import os
os.environ["PATH"] += os.pathsep + os.path.dirname("/usr/bin")

import asyncio
from tools.tiktok_scraper import get_trending_anime_edits
from tools.audio_downloader import download_audio
from tools.content_gatherer import get_anime_clips
from agents.orchestrator import create_editing_plan, generate_search_queries
from agents.executor import execute_editing_plan
import imageio_ffmpeg

# Add ffmpeg to PATH for yt-dlp and moviepy
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

async def run_agent():
    print("=== Anime Edit Multi-Agent Pipeline ===\n")
    
    # Step 1: Find trending edits
    print("[Step 1] Finding trending anime edits...")
    trending_videos = await get_trending_anime_edits(count=3)
    
    if not trending_videos:
        print("No trending videos found. Using fallback/mock data.")
        trending_videos = [{
            "video_id": "fallback_phonk",
            "video_url": "https://www.youtube.com/watch?v=w-sQRS-Lc9k",
            "sound_id": "phonk_sound",
            "sound_title": "Murder In My Mind",
            "sound_author": "Kordhell",
            "caption": "Phonk Anime Edit #phonk #anime",
            "play_url": ""
        }]
        print("Using fallback video: Kordhell - Murder In My Mind")

    top_video = trending_videos[0]
    print(f"✓ Selected: {top_video['caption']} (Sound: {top_video['sound_title']})")
    
    # Step 2: Download audio
    print("\n[Step 2] Downloading audio...")
    audio_path = f"output/audio/{top_video['sound_id']}.mp3"
    downloaded_audio = download_audio(top_video['video_url'], audio_path)
    
    if not downloaded_audio:
        print("Failed to download audio.")
        return
    print(f"✓ Audio: {downloaded_audio}")
    
    # Step 3: ORCHESTRATOR AGENT - Generate search queries
    print("\n[Step 3] Orchestrator Agent: Generating search queries...")
    search_queries = generate_search_queries(top_video)
    print(f"✓ Generated {len(search_queries)} queries")
    
    # Gather clips using generated queries
    print("\n[Step 4] Gathering anime clips...")
    all_clips = []
    for query in search_queries[:2]:  # Use first 2 queries
        print(f"  Query: '{query}'")
        clips = get_anime_clips(query, count=3)
        all_clips.extend(clips)
    
    # Deduplicate
    all_clips = list(set(all_clips))
    print(f"✓ Found {len(all_clips)} unique clips")
    
    if not all_clips:
        print("No clips found.")
        return
    
    # Step 5: ORCHESTRATOR AGENT - Create editing plan
    print("\n[Step 5] Orchestrator Agent: Creating editing plan...")
    
    # Generate creative temperature (0.3-0.8 for variety)
    import random
    temperature = random.uniform(0.3, 0.8)
    
    editing_plan = create_editing_plan(
        audio_path=downloaded_audio,
        tiktok_metadata=top_video,
        clip_paths=all_clips,
        temperature=temperature
    )
    
    # Step 6: EXECUTOR AGENT - Build video
    print("\n[Step 6] Executor Agent: Building final video...")
    output_file = "output/final_edit.mp4"
    final_edit = execute_editing_plan(
        plan=editing_plan,
        audio_path=downloaded_audio,
        video_paths=all_clips,
        output_path=output_file
    )
    
    if final_edit:
        print(f"\n🎉 SUCCESS! Final edit: {final_edit}")
    else:
        print("\n❌ Failed to create edit.")

if __name__ == "__main__":
    asyncio.run(run_agent())
