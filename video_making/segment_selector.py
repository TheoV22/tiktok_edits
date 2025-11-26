"""
Intelligent audio segment selector for finding the best part of a song.
Analyzes audio to find calm intro and rage drop sections.
"""
import numpy as np
from moviepy import AudioFileClip

def find_best_segment(audio_path: str, target_duration: float = 12.0, pattern: str = "calm-rage") -> dict:
    """
    Finds the best segment of an audio track matching the desired pattern.
    
    Args:
        audio_path: Path to audio file
        target_duration: Desired segment duration in seconds
        pattern: Desired intensity pattern (e.g., 'calm-rage', 'rage-calm', 'calm-rage-calm')
    
    Returns:
        dict: {
            'start_time': segment start in seconds,
            'end_time': segment end in seconds,
            'duration': segment duration,
            'calm_end': timestamp where rage starts (within segment) or None
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
        
        # Pattern-based segment selection
        target_windows = int(target_duration)
        best_score = -1
        best_start = 0
        calm_end_time = target_duration * 0.6  # Default
        
        # Define pattern scoring functions
        if pattern == "calm-rage":
            # Low energy start, high energy end
            for start_window in range(len(energies) - target_windows):
                segment = energies[start_window:start_window + target_windows]
                intro = np.mean(segment[:int(target_windows * 0.4)])
                drop = np.mean(segment[int(target_windows * 0.5):])
                score = drop - intro
                if score > best_score:
                    best_score, best_start = score, start_window
                    calm_end_time = start_window + np.argmax(segment)
        
        elif pattern == "rage-calm":
            # High energy start, low energy end
            for start_window in range(len(energies) - target_windows):
                segment = energies[start_window:start_window + target_windows]
                intro = np.mean(segment[:int(target_windows * 0.4)])
                outro = np.mean(segment[int(target_windows * 0.6):])
                score = intro - outro
                if score > best_score:
                    best_score, best_start = score, start_window
                    calm_end_time = start_window + int(target_windows * 0.7)
        
        elif pattern == "calm-rage-calm":
            # Low-high-low arc
            for start_window in range(len(energies) - target_windows):
                segment = energies[start_window:start_window + target_windows]
                intro = np.mean(segment[:int(target_windows * 0.3)])
                mid = np.mean(segment[int(target_windows * 0.4):int(target_windows * 0.6)])
                outro = np.mean(segment[int(target_windows * 0.7):])
                score = mid - (intro + outro) / 2
                if score > best_score:
                    best_score, best_start = score, start_window
                    calm_end_time = start_window + int(target_windows * 0.4)
        
        elif "rage" in pattern and pattern.count("rage") >= 2:
            # High energy throughout
            for start_window in range(len(energies) - target_windows):
                segment = energies[start_window:start_window + target_windows]
                score = np.mean(segment)
                if score > best_score:
                    best_score, best_start = score, start_window
                    calm_end_time = None  # No calm section
        
        elif "calm" in pattern and pattern.count("calm") >= 2:
            # Low energy throughout
            for start_window in range(len(energies) - target_windows):
                segment = energies[start_window:start_window + target_windows]
                score = -np.mean(segment)  # Prefer low energy
                if score > best_score:
                    best_score, best_start = score, start_window
                    calm_end_time = None  # All calm
        
        else:
            # Default to calm-rage for unknown patterns
            for start_window in range(len(energies) - target_windows):
                segment = energies[start_window:start_window + target_windows]
                intro = np.mean(segment[:int(target_windows * 0.4)])
                drop = np.mean(segment[int(target_windows * 0.5):])
                score = drop - intro
                if score > best_score:
                    best_score, best_start = score, start_window
                    calm_end_time = start_window + np.argmax(segment)
        
        # Calculate final segment times
        start_time = best_start
        end_time = start_time + target_duration
        
        audio_clip.close()
        
        return {
            'start_time': float(start_time),
            'end_time': float(end_time),
            'duration': target_duration,
            'calm_end': float(calm_end_time) if calm_end_time is not None else None
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
