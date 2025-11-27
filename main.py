import os
os.environ["PATH"] += os.pathsep + os.path.dirname("/usr/bin")

import asyncio
from trend_discovery.discovery import get_trending_anime_edits_v2
from content_download.audio import download_audio
from content_download.clips import get_anime_clips
from video_making.orchestrator import create_editing_plan, generate_search_queries
from video_making.executor import execute_editing_plan
import imageio_ffmpeg

# Add ffmpeg to PATH for yt-dlp and moviepy
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

async def run_agent():
    print("=== Anime Edit Multi-Agent Pipeline ===\n")

    # Step 0: Initialize or clean directories
    # TODO: remove all clips and audio files from previous runs to start fresh
    
    # Step 1: Find trending edits (Data-Driven)
    print("[Step 1] Finding trending anime edits (Data-Driven)...")
    # Use temperature=0.5 for balanced creativity (1-2 anime)
    trending_result = await get_trending_anime_edits_v2(count=8, temperature=0.5)
    
    if not trending_result:
        print("❌ All trending sources failed. Exiting.")
        return

    selected_animes = trending_result['selected_animes']
    song_data = trending_result['song']
    audio_path = trending_result['audio_path']
    clip_paths = trending_result['clip_paths']
    metadata = trending_result['metadata']
    
    print(f"✓ Selected Anime: {', '.join(selected_animes)}")
    print(f"✓ Song: {song_data['sound_title']} by {song_data['sound_author']}")
    print(f"✓ Audio: {audio_path}")
    print(f"✓ Clips: {len(clip_paths)} clips gathered")
    
    # Step 2: ORCHESTRATOR AGENT - Create Plan
    print("\n[Step 2] Orchestrator Agent: Creating editing plan...")
    
    # Create plan using gathered assets
    editing_plan = create_editing_plan(
        audio_path=audio_path,
        tiktok_metadata=song_data, # Use song metadata as base
        clip_paths=clip_paths,
        temperature=0.5
    )
    
    # Step 3: EXECUTOR AGENT - Build video
    print("\n[Step 3] Executor Agent: Building final video...")
    output_file = "output/final_edit.mp4"
    final_edit = execute_editing_plan(
        plan=editing_plan,
        audio_path=audio_path,
        video_paths=clip_paths,
        output_path=output_file
    )
    
    if final_edit:
        print(f"\n🎉 SUCCESS! Final edit: {final_edit}")
    else:
        print("\n❌ Failed to create edit.")

if __name__ == "__main__":
    asyncio.run(run_agent())
