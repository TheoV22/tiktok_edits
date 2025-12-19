
import asyncio
import os
import shutil
from content_download.clips import get_high_quality_clips

async def main():
    anime = "Jujutsu Kaisen"
    print(f"Testing clip downloader for: {anime}")
    
    # Clean previous output
    output_dir = "output/test_clips"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Test only youtube_hq source
    clips = await get_high_quality_clips(
        anime_title=anime,
        count=1,
        sources=['youtube_hq'],
        output_dir=output_dir
    )
    
    print("\nDownloaded clips:")
    for clip in clips:
        print(f"- {clip} (Size: {os.path.getsize(clip) / 1024 / 1024:.2f} MB)")
        
    if not clips:
        print("No clips found!")

if __name__ == "__main__":
    asyncio.run(main())
