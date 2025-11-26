"""
Beat detection using MoviePy and numpy for Python 3.14 compatibility.
"""
import numpy as np
from moviepy import AudioFileClip

def detect_beats(audio_path: str, min_interval_s:float = 0.3) -> dict:
    """
    Detects beats in an audio file using energy-based peak detection.
    
    Args:
        audio_path: Path to audio file
        min_interval_s: Minimum time between beats in seconds
    
    Returns:
        dict: {
            'beat_times': list of beat timestamps in seconds,
            'tempo': estimated BPM,
            'beat_frames': beat indices
        }
    """
    try:
        # Load audio using MoviePy
        audio_clip = AudioFileClip(audio_path)
        
        # Get audio as numpy array
        fps = audio_clip.fps  # Sample rate
        audio_array = audio_clip.to_soundarray(fps=fps)
        
        # Convert to mono if stereo
        if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
            audio_array = np.mean(audio_array, axis=1)
        
        # Chunk size for analysis (50ms chunks)
        chunk_duration = 0.05  # 50ms
        chunk_samples = int(fps * chunk_duration)
        
        # Calculate energy for each chunk
        energies = []
        num_chunks = len(audio_array) // chunk_samples
        
        for i in range(num_chunks):
            start_idx = i * chunk_samples
            end_idx = start_idx + chunk_samples
            chunk = audio_array[start_idx:end_idx]
            
            # Calculate RMS energy
            energy = np.sqrt(np.mean(chunk**2))
            energies.append(energy)
        
        energies = np.array(energies)
        
        # Find peaks in energy (potential beats)
        # Use adaptive threshold
        threshold = np.mean(energies) + 0.5 * np.std(energies)
        
        beat_chunks = []
        min_interval_chunks = int(min_interval_s / chunk_duration)
        
        for i in range(len(energies)):
            # Check if this is a local maximum above threshold
            if energies[i] > threshold:
                is_peak = True
                # Check if there's a higher peak nearby
                start = max(0, i - min_interval_chunks)
                end = min(len(energies), i + min_interval_chunks)
                for j in range(start, end):
                    if j != i and energies[j] > energies[i]:
                        is_peak = False
                        break
                
                if is_peak:
                    beat_chunks.append(i)
        
        # Convert chunk indices to time
        beat_times = [chunk_idx * chunk_duration for chunk_idx in beat_chunks]
        
        # Estimate tempo from beat intervals
        if len(beat_times) > 1:
            intervals = np.diff(beat_times)
            avg_interval = np.median(intervals)
            tempo = 60.0 / avg_interval if avg_interval > 0 else 120.0
        else:
            tempo = 120.0
        
        audio_clip.close()
        
        return {
            'beat_times': beat_times,
            'tempo': float(tempo),
            'beat_frames': beat_chunks
        }
    except Exception as e:
        print(f"Error detecting beats: {e}")
        import traceback
        traceback.print_exc()
        # Return fallback: beats every 0.5s at 120 BPM
        try:
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
            audio_clip.close()
        except:
            duration = 30.0
        fallback_beats = list(np.arange(0, duration, 0.5))
        return {
            'beat_times': fallback_beats,
            'tempo': 120.0,
            'beat_frames': list(range(len(fallback_beats)))
        }

def get_audio_intensity_segments(audio_path: str, beat_times: list) -> list:
    """
    Calculates the intensity (RMS energy) of audio segments between beats.
    
    Returns:
        list: Intensity values (0.0-1.0) for each segment between beats
    """
    try:
        audio_clip = AudioFileClip(audio_path)
        fps = audio_clip.fps
        audio_array = audio_clip.to_soundarray(fps=fps)
        
        # Convert to mono if stereo
        if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
            audio_array = np.mean(audio_array, axis=1)
        
        intensities = []
        for i in range(len(beat_times) - 1):
            start_sample = int(beat_times[i] * fps)
            end_sample = int(beat_times[i + 1] * fps)
            
            if end_sample > len(audio_array):
                end_sample = len(audio_array)
            
            segment = audio_array[start_sample:end_sample]
            
            if len(segment) > 0:
                rms = np.sqrt(np.mean(segment**2))
                intensities.append(float(rms))
            else:
                intensities.append(0.0)
        
        # Normalize to 0-1 range
        if intensities:
            max_intensity = max(intensities)
            if max_intensity > 0:
                intensities = [i / max_intensity for i in intensities]
        
        audio_clip.close()
        return intensities
    except Exception as e:
        print(f"Error calculating audio intensity: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) > 1:
        result = detect_beats(sys.argv[1])
        print(f"Detected {len(result['beat_times'])} beats at {result['tempo']:.1f} BPM")
        print(f"Beat times: {result['beat_times'][:10]}...")
