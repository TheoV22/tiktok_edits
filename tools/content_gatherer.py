import imageio_ffmpeg
import os
import subprocess
import glob

def get_anime_clips(query: str, count: int = 3, output_dir: str = "output/clips"):
    """
    Searches for and downloads anime clips from YouTube using yt-dlp.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # yt-dlp search query
    # ytsearch{count}:{query}
    search_query = f"ytsearch{count}:{query}"
    
    # Output template: output_dir/video_id.ext
    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--ffmpeg-location", ffmpeg_exe,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--max-filesize", "50M", # Limit size to avoid downloading full episodes if possible
        "-o", output_template,
        search_query
    ]
    
    try:
        subprocess.run(cmd, check=True)
        
        # Return list of downloaded files
        # We can scan the directory for recent files or just return all files in it for now
        # A better way is to capture stdout of yt-dlp to get filenames, but simple glob is easier for MVP
        files = glob.glob(os.path.join(output_dir, "*"))
        # Filter for valid video extensions and ignore .part files
        valid_extensions = {'.mp4', '.mkv', '.webm', '.mov'}
        video_files = [f for f in files if os.path.splitext(f)[1].lower() in valid_extensions and not f.endswith('.part')]
        return video_files
    except subprocess.CalledProcessError as e:
        print(f"Error gathering clips: {e}")
        return []
