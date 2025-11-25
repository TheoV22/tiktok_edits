import imageio_ffmpeg
import os
import subprocess

def download_audio(video_url: str, output_path: str):
    """
    Downloads audio from a TikTok video URL using yt-dlp.
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # yt-dlp command to extract audio
    # -x: Extract audio
    # --audio-format mp3: Convert to mp3
    # -o: Output template
    cmd = [
        "yt-dlp",
        "--ffmpeg-location", ffmpeg_exe,
        "-x",
        "--audio-format", "mp3",
        "-o", output_path,
        video_url
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        # yt-dlp might append .mp3 to the filename if not present in template, 
        # but if we specify full path in -o, it usually respects it but might add extension.
        # Let's ensure we return the actual file path.
        expected_path = output_path
        if not expected_path.endswith(".mp3"):
            expected_path += ".mp3"
            
        # Check if file exists (yt-dlp might have added extension)
        if os.path.exists(expected_path):
            return expected_path
        elif os.path.exists(output_path):
             return output_path
        else:
            # Try finding it
            base, _ = os.path.splitext(output_path)
            if os.path.exists(base + ".mp3"):
                return base + ".mp3"
            
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Error downloading audio: {e.stderr.decode()}")
        return None
