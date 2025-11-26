"""
Orchestrator Agent using Google ADK.
Analyzes TikTok metadata, audio, and clips to create an intelligent editing plan.
"""
from google import genai
from google.genai.types import Tool, FunctionDeclaration, Schema, Type
import json
import os
from video_making.beat_detector import detect_beats, get_audio_intensity_segments
from video_making.clip_classifier import classify_multiple_clips
from video_making.segment_selector import find_best_segment

# Initialize Gemini client with API key from environment
# If not set, will use a fallback non-LLM approach
try:
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    if api_key:
        client = genai.Client(api_key=api_key)
        USE_LLM = True
    else:
        client = None
        USE_LLM = False
        print("⚠️  No GOOGLE_API_KEY found. Using fallback query generation.")
except Exception as e:
    client = None
    USE_LLM = False
    print(f"⚠️  Could not initialize Gemini client: {e}. Using fallback.")

def generate_search_queries(tiktok_metadata: dict) -> list[str]:
    """
    Uses LLM to generate intelligent search queries from TikTok metadata.
    Falls back to simple extraction if LLM not available.
    
    Args:
        tiktok_metadata: Dict with 'caption', 'sound_title', etc.
    
    Returns:
        List of search query strings
    """
    # Fallback if no LLM
    if not USE_LLM or client is None:
        caption = tiktok_metadata.get('caption', '').lower()
        queries = []
        
        # Extract anime names
        anime_keywords = ['naruto', 'jujutsu', 'demon slayer', 'attack on titan', 'bleach', 'one piece']
        for keyword in anime_keywords:
            if keyword in caption:
                queries.append(f"{keyword} fight scene 4k")
                queries.append(f"{keyword} epic moment hd")
        
        # Generic queries
        if not queries:
            queries = ["anime fight scene 4k", "anime epic moment hd"]
        
        return queries[:5]
    
    # Use LLM
    prompt = f"""Based on this TikTok metadata, generate 3-5 diverse search queries to find anime clips on YouTube:

Caption: {tiktok_metadata.get('caption', '')}
Sound: {tiktok_metadata.get('sound_title', '')}
Hashtags: {tiktok_metadata.get('caption', '')}

The queries should:
1. Extract anime names/characters mentioned
2. Include descriptive terms like "fight", "rage", "epic", "sad", etc.
3. Add quality keywords like "4k", "hd", "best"
4. Be diverse to find different types of clips

Return ONLY a JSON array of query strings, no markdown or explanation:
["query1", "query2", "query3"]"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        
        # Extract JSON from response
        text = response.text.strip()
        # Remove markdown code blocks if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            text = text.rsplit('\n', 1)[0]
        if text.startswith('json'):
            text = text[4:].strip()
        
        queries = json.loads(text)
        return queries if isinstance(queries, list) else [queries]
    except Exception as e:
        print(f"Error generating queries with LLM: {e}")
        # Fallback
        caption = tiktok_metadata.get('caption', '').lower()
        return [f"anime fight scene 4k", f"{caption} anime"]


def select_editing_pattern(audio_path: str, temperature: float = 0.5) -> str:
    """
    Selects creative editing pattern based on audio analysis and temperature.
    
    Args:
        audio_path: Path to audio file
        temperature: Creativity level (0.0-1.0)
    
    Returns:
        Pattern string: 'calm-rage', 'rage-calm', 'calm-rage-calm', etc.
    """
    import random
    
    # Available patterns
    patterns = [
        'calm-rage',           # Traditional buildup
        'rage-calm',           # Intense start, chill end
        'calm-rage-calm',      # Rise and fall
        'calm-calm-rage',      # Extended buildup
        'rage-rage-calm',      # Intense opening
        'calm-calm-calm',      # Chill vibes
        'rage-rage-rage'       # Maximum intensity
    ]
    
    # High temperature = more random selection
    # Low temperature = prefer traditional patterns
    if temperature > 0.7:
        # High creativity - any pattern
        return random.choice(patterns)
    elif temperature > 0.4:
        # Medium creativity - prefer varied patterns
        weights = [0.2, 0.15, 0.25, 0.15, 0.1, 0.05, 0.1]
        return random.choices(patterns, weights=weights)[0]
    else:
        # Low creativity - prefer traditional
        weights = [0.5, 0.2, 0.15, 0.1, 0.03, 0.01, 0.01]
        return random.choices(patterns, weights=weights)[0]

def select_editing_intensity(temperature: float = 0.5) -> str:
    """
    Selects editing intensity based on temperature.
    
    Returns:
        'low', 'medium', or 'high'
    """
    import random
    
    if temperature > 0.7:
        # High temp favors varied/high intensity
        return random.choice(['medium', 'high', 'high'])
    elif temperature > 0.3:
        # Medium temp balanced
        return random.choice(['low', 'medium', 'medium', 'high'])
    else:
        # Low temp conservative
        return random.choice(['low', 'low', 'medium'])

def select_duration(clip_count: int, temperature: float = 0.5) -> float:
    """
    Dynamically selects video duration based on clips and temperature.
    
    Args:
        clip_count: Number of available clips
        temperature: Creativity level
    
    Returns:
        Duration in seconds (6-20s range)
    """
    import random
    
    # Base duration from clip count
    if clip_count >= 10:
        base_min, base_max = 14, 20
    elif clip_count >= 5:
        base_min, base_max = 10, 16
    elif clip_count >= 3:
        base_min, base_max = 8, 12
    else:
        base_min, base_max = 6, 10
    
    # Temperature affects variance
    if temperature > 0.6:
        # High temp = wider range
        duration = random.uniform(base_min - 2, base_max + 2)
    elif temperature > 0.3:
        # Medium temp = moderate range
        duration = random.uniform(base_min, base_max)
    else:
        # Low temp = narrow, predictable
        duration = (base_min + base_max) / 2
    
    # Clamp to 6-20s
    return max(6.0, min(20.0, duration))

def create_editing_plan(audio_path: str, tiktok_metadata: dict, clip_paths: list[str], temperature: float = 0.5) -> dict:
    """
    Orchestrator agent that creates a comprehensive editing plan with creative temperature.
    
    Args:
        audio_path: Path to audio file
        tiktok_metadata: TikTok video metadata
        clip_paths: List of available video clips
        temperature: Creativity level (0.0-1.0)
    
    Returns:
        Editing plan dict
    """
    print("\n=== Orchestrator Agent: Creating Editing Plan ===")
    print(f"🌡️  Temperature: {temperature:.2f} ({'Low' if temperature < 0.3 else 'Medium' if temperature < 0.7 else 'High'} creativity)")
    
    # Step 1: Generate smart search queries
    print("Generating search queries from metadata...")
    search_queries = generate_search_queries(tiktok_metadata)
    print(f"Generated queries: {search_queries}")
    
    # Step 2: Classify clips
    print("Analyzing clip emotions...")
    clip_classifications = classify_multiple_clips(clip_paths) if clip_paths else {}
    
    # Step 3: Creative selections based on temperature
    print("Making creative decisions...")
    
    # Select pattern
    pattern = select_editing_pattern(audio_path, temperature)
    print(f"📐 Pattern: {pattern}")
    
    # Select intensity
    intensity = select_editing_intensity(temperature)
    print(f"⚡ Intensity: {intensity}")
    
    # Select duration
    target_duration = select_duration(len(clip_paths), temperature)
    print(f"⏱️  Duration: {target_duration:.1f}s")
    
    # Step 4: Analyze audio with pattern
    print("Analyzing audio structure...")
    from video_making.segment_selector import find_best_segment
    
    segment_info = find_best_segment(audio_path, target_duration=target_duration, pattern=pattern)
    beat_data = detect_beats(audio_path)
    
    # Adjust beats to segment
    beat_times_full = beat_data['beat_times']
    beat_times = [b - segment_info['start_time'] for b in beat_times_full 
                 if segment_info['start_time'] <= b <= segment_info['end_time']]
    
    # Get intensities
    intensities_full = get_audio_intensity_segments(audio_path, beat_times_full)
    intensities = []
    for i in range(len(beat_times) - 1):
        beat_start_abs = beat_times[i] + segment_info['start_time']
        for j, bt in enumerate(beat_times_full[:-1]):
            if abs(bt - beat_start_abs) < 0.1:
                if j < len(intensities_full):
                    intensities.append(intensities_full[j])
                break
    
    # Step 5: Create beat assignments
    print("Creating beat-to-clip assignments...")
    
    # Calculate calm end relative to segment (can be None for rage-only patterns)
    if segment_info['calm_end'] is not None:
        calm_end_relative = segment_info['calm_end'] - segment_info['start_time']
    else:
        calm_end_relative = None  # No calm section in this pattern
    
    # Calculate proportional fade durations
    # Shorter videos (8s) = 0.3s fades, longer videos (15s) = 0.5s fades
    if target_duration <= 8:
        fade_duration = 0.3
    elif target_duration <= 12:
        fade_duration = 0.4
    else:
        fade_duration = 0.5
    
    print(f"Fade duration: {fade_duration}s (proportional to {target_duration}s video)")
    
    beat_assignments = []
    
    for i in range(len(beat_times) - 1):
        beat_start = beat_times[i]
        intensity = intensities[i] if i < len(intensities) else 0.5
        
        # Determine clip type based on pattern
        if calm_end_relative is None:
            # No calm section - use pattern to determine
            if "rage" in pattern:
                clip_type = "rage" if intensity > 0.5 else "mixed"
            else:
                clip_type = "calm" if intensity < 0.5 else "mixed"
        else:
            # Pattern has calm/rage sections
            if beat_start < calm_end_relative:
                clip_type = "calm" if intensity < 0.7 else "mixed"
            else:
                clip_type = "rage" if intensity > 0.3 else "mixed"
        
        # Determine effects
        effects = []
        if i == 0:
            effects.append({"type": "fade_in", "duration": fade_duration})
        if i == len(beat_times) - 2:
            effects.append({"type": "fade_out", "duration": fade_duration})
        effects.append({"type": "flash"})
        effects.append({"type": "zoom_pulse"})
        
        beat_assignments.append({
            "beat_idx": i,
            "beat_time": beat_times[i],
            "clip_type": clip_type,
            "intensity": intensity,
            "effects": effects
        })
    
    plan = {
        "target_duration": target_duration,
        "audio_segment": {
            "start": segment_info['start_time'],
            "end": segment_info['end_time'],
            "calm_end": calm_end_relative
        },
        "search_queries": search_queries,
        "beat_times": beat_times,
        "beat_assignments": beat_assignments,
        "clip_classifications": clip_classifications,
        "fade_duration": fade_duration,
        "pattern": pattern,
        "intensity": intensity,
        "temperature": temperature
    }
    
    print(f"\n=== Editing Plan Created ===")
    print(f"Duration: {target_duration:.1f}s")
    print(f"Pattern: {pattern}")
    print(f"Intensity: {intensity}")
    print(f"Beats: {len(beat_times)}")
    if calm_end_relative is not None:
        print(f"Transition at: {calm_end_relative:.1f}s")
    print(f"Fade duration: {fade_duration}s")
    
    return plan

if __name__ == "__main__":
    # Test
    test_metadata = {
        "caption": "Epic Naruto fight scene #naruto #anime",
        "sound_title": "Phonk Music"
    }
    queries = generate_search_queries(test_metadata)
    print(f"Test queries: {queries}")
