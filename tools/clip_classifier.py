import cv2
import numpy as np
from moviepy import VideoFileClip

def classify_clip_emotion(video_path: str) -> dict:
    """
    Classifies a video clip's emotion/intensity based on motion analysis.
    
    Uses optical flow to detect motion intensity:
    - High motion = epic/rage (action scenes, fast movements)
    - Low motion = sad/calm (slow scenes, static shots)
    
    Returns:
        dict: {
            'emotion': 'epic' | 'rage' | 'calm' | 'sad',
            'intensity': 0.0-1.0,
            'motion_score': raw motion metric
        }
    """
    try:
        cap = cv2.VideoCapture(video_path)
        
        # Read first frame
        ret, prev_frame = cap.read()
        if not ret:
            return {'emotion': 'calm', 'intensity': 0.5, 'motion_score': 0.0}
        
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        
        motion_scores = []
        frame_count = 0
        max_frames = 30  # Sample max 30 frames for performance
        
        while True:
            ret, frame = cap.read()
            if not ret or frame_count >= max_frames:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate optical flow (motion between frames)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray, None, 
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            
            # Calculate magnitude of motion
            magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
            motion_score = np.mean(magnitude)
            motion_scores.append(motion_score)
            
            prev_gray = gray
            frame_count += 1
        
        cap.release()
        
        if not motion_scores:
            return {'emotion': 'calm', 'intensity': 0.5, 'motion_score': 0.0}
        
        avg_motion = np.mean(motion_scores)
        
        # Classify based on motion thresholds
        # These thresholds are heuristic and may need tuning
        if avg_motion > 2.0:
            emotion = 'rage'
            intensity = min(1.0, avg_motion / 4.0)
        elif avg_motion > 1.0:
            emotion = 'epic'
            intensity = min(0.9, avg_motion / 3.0)
        elif avg_motion > 0.5:
            emotion = 'calm'
            intensity = avg_motion / 2.0
        else:
            emotion = 'sad'
            intensity = avg_motion
        
        return {
            'emotion': emotion,
            'intensity': float(intensity),
            'motion_score': float(avg_motion)
        }
        
    except Exception as e:
        print(f"Error classifying clip {video_path}: {e}")
        return {'emotion': 'calm', 'intensity': 0.5, 'motion_score': 0.0}

def classify_multiple_clips(video_paths: list) -> dict:
    """
    Classifies multiple clips and returns a mapping.
    
    Returns:
        dict: {video_path: classification_result}
    """
    results = {}
    for path in video_paths:
        print(f"Classifying {path}...")
        results[path] = classify_clip_emotion(path)
        print(f"  -> {results[path]['emotion']} (intensity: {results[path]['intensity']:.2f})")
    return results

if __name__ == "__main__":
    # Simple test
    import sys
    if len(sys.argv) > 1:
        result = classify_clip_emotion(sys.argv[1])
        print(f"Emotion: {result['emotion']}, Intensity: {result['intensity']:.2f}, Motion: {result['motion_score']:.2f}")
