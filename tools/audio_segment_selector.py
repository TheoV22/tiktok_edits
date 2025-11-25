"""
Intelligent audio segment selector for finding the best part of a song.
Analyzes audio to find calm intro and rage drop sections.
"""
import numpy as np
from moviepy import AudioFileClip

def find_best_segment(audio_path: str, target_duration: float = 12.0) -> dict:
    """
    Finds the best segment of an audio track with calm intro and rage drop.
    
    Args:
        audio_path: Path to audio file
        target_duration: Desired segment duration in seconds
    
    Returns:
        dict: {
            'start_time': segment start in seconds,
            'end_time': segment end in seconds,
            'duration': segment duration,
            'calm_end': timestamp where rage starts (within segment)
        }
    """
    try:
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        
        # If audio is shorter than target, use entire audio
        if total_duration <= target_duration:
            audio_clip.close()
            return {
                'start_time': 0,
                'end_time': total_duration,
                'duration': total_duration,
                'calm_end': total_duration * 0.6  # 60% mark
            }
        
        # Get audio array
        fps = audio_clip.fps
        audio_array = audio_clip.to_soundarray(fps=fps)
        
        # Convert to mono if stereo
        if len(audio_array.shape) > 1 and audio_array.shape[1] > 1:
            audio_array = np.mean(audio_array, axis=1)
        
        # Analyze energy in 1-second windows
        window_size = fps  # 1 second
        num_windows = len(audio_array) // window_size
        
        energies = []
        for i in range(num_windows):
            start_idx = i * window_size
            end_idx = start_idx + window_size
            window = audio_array[start_idx:end_idx]
            energy = np.sqrt(np.mean(window**2))
            energies.append(energy)
        
        energies = np.array(energies)
        
        # Find segments with calm start and intense middle/end
        best_score = -1
        best_start = 0
        
        target_windows = int(target_duration)
        
        for start_window in range(len(energies) - target_windows):
            segment_energies = energies[start_window:start_window + target_windows]
            
            # Score based on: low energy at start, high energy at end
            intro_energy = np.mean(segment_energies[:int(target_windows * 0.4)])  # First 40%
            drop_energy = np.mean(segment_energies[int(target_windows * 0.5):])  # Last 50%
            
            # Good segment has calm intro and rage drop
            score = drop_energy - intro_energy  # Maximize difference
            
            if score > best_score:
                best_score = score
                best_start = start_window
        
        start_time = best_start
        end_time = start_time + target_duration
        
        # Find where the drop happens (max energy spike) within segment
        segment_energies = energies[best_start:best_start + target_windows]
        drop_idx = int(best_start + np.argmax(segment_energies))
        calm_end_time = drop_idx
        
        audio_clip.close()
        
        return {
            'start_time': float(start_time),
            'end_time': float(end_time),
            'duration': target_duration,
            'calm_end': float(calm_end_time)
        }
        
    except Exception as e:
        print(f"Error finding best segment: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: use start of audio
        return {
            'start_time': 0,
            'end_time': min(target_duration, 30),
            'duration': min(target_duration, 30),
            'calm_end': target_duration * 0.6
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = find_best_segment(sys.argv[1])
        print(f"Best segment: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
        print(f"Calm ends at: {result['calm_end']:.1f}s, then rage begins")
