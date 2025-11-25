import imageio_ffmpeg
import os
import sys

exe = imageio_ffmpeg.get_ffmpeg_exe()
print(f"ffmpeg exe: {exe}")
print(f"dirname: {os.path.dirname(exe)}")
print(f"exists: {os.path.exists(exe)}")

# Check if 'ffmpeg' is in the directory
files = os.listdir(os.path.dirname(exe))
print(f"files in dir: {files}")
