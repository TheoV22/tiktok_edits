import asyncio
import os
from tools.tiktok_scraper import get_trending_anime_edits
from tools.audio_downloader import download_audio
from tools.content_gatherer import get_anime_clips
from tools.video_editor import create_anime_edit
import imageio_ffmpeg

# Add ffmpeg to PATH for yt-dlp and moviepy
os.environ["PATH"] += os.pathsep + os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

# Mock ADK Agent structure for simplicity and robustness in this environment
# In a real ADK setup, we would define tools and an agent class.
# Here we implement the "uninterrupted pipeline" mode directly.

async def run_agent():
    print("--- Starting Anime Edit Agent ---")
    
    # Step 1: Find trending edits
    print("\n[Step 1] Finding trending anime edits...")
    trending_videos = await get_trending_anime_edits(count=3)
    
    if not trending_videos:
        print("No trending videos found. Using fallback/mock data.")
        # Fallback data
        trending_videos = [{
            "video_id": "fallback_phonk",
            "video_url": "https://www.youtube.com/watch?v=w-sQRS-Lc9k", # Kordhell - Murder In My Mind
            "sound_id": "phonk_sound",
            "sound_title": "Murder In My Mind",
            "sound_author": "Kordhell",
            "caption": "Phonk Anime Edit #phonk #anime",
            "play_url": ""
        }]
        print("Using fallback video: Kordhell - Murder In My Mind")

    # Pick the top one
    top_video = trending_videos[0]
    print(f"Top video found: {top_video['caption']} (Sound: {top_video['sound_title']})")
    
    # Step 2: Download audio
    print("\n[Step 2] Downloading audio...")
    audio_path = f"output/audio/{top_video['sound_id']}.mp3"
    downloaded_audio = download_audio(top_video['video_url'], audio_path)
    
    if not downloaded_audio:
        print("Failed to download audio.")
        return
    print(f"Audio downloaded to: {downloaded_audio}")
    
    # Step 3: Gather anime clips
    # Extract a keyword from caption or just use "anime fight" if generic
    # Simple keyword extraction: look for hashtags or just use "anime"
    query = "anime fight scene 4k" # Added 4k for better quality potential
    if "naruto" in top_video['caption'].lower():
        query = "naruto fight badass"
    elif "jujutsu" in top_video['caption'].lower():
        query = "jujutsu kaisen fight 4k"
        
    print(f"\n[Step 3] Gathering clips for query: '{query}'...")
    # Increase count to ensure enough footage for 30s (assuming 2-3s cuts)
    clips = get_anime_clips(query, count=6)
    
    if not clips:
        print("No clips found.")
        return
    print(f"Clips found: {clips}")
    
    # Step 4: Create Edit
    print("\n[Step 4] Creating video edit...")
    output_file = "output/final_edit.mp4"
    final_edit = create_anime_edit(downloaded_audio, clips, output_file)
    
    if final_edit:
        print(f"\nSUCCESS! Final edit saved to: {final_edit}")
    else:
        print("\nFailed to create edit.")

if __name__ == "__main__":
    asyncio.run(run_agent())
