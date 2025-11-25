from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx
import numpy as np
import os
import random
from tools.beat_detector import detect_beats, get_audio_intensity_segments
from tools.clip_classifier import classify_multiple_clips
from tools.audio_segment_selector import find_best_segment

def create_anime_edit(audio_path: str, video_paths: list[str], output_path: str):
    """
    Creates a beat-synced anime edit with emotion-aware clip selection and intelligent audio selection.
    """
    try:
        # STEP 0: Find the best audio segment (calm intro + rage drop)
        print("Analyzing audio for best segment...")
        segment_info = find_best_segment(audio_path, target_duration=12.0)
        print(f"Selected segment: {segment_info['start_time']:.1f}s - {segment_info['end_time']:.1f}s")
        print(f"Rage drop at: {segment_info['calm_end']:.1f}s")
        
        # Load audio with intelligent segment selection
        audio_full = AudioFileClip(audio_path)
        audio = audio_full.subclipped(segment_info['start_time'], segment_info['end_time'])
        audio_duration = audio.duration
        
        from moviepy import afx
        
        # Apply audio fade-in/out for smooth transitions
        audio = audio.with_effects([
            afx.AudioFadeIn(0.5),
            afx.AudioFadeOut(0.5)
        ])
        
        # STEP 1: Detect beats
        print("Detecting beats...")
        beat_data = detect_beats(audio_path)
        beat_times_full = beat_data['beat_times']
        
        # Adjust beat times to selected segment
        beat_times = [b - segment_info['start_time'] for b in beat_times_full 
                     if segment_info['start_time'] <= b <= segment_info['end_time']]
        
        if not beat_times or len(beat_times) < 2:
            print("No beats detected in segment, using fallback timing")
            beat_times = list(np.arange(0, audio_duration, 0.5))
        
        print(f"Found {len(beat_times)} beats at {beat_data['tempo']:.1f} BPM in segment")
        
        # STEP 2: Get audio intensity for each beat segment
        print("Analyzing audio intensity...")
        # Detect on full audio then filter
        intensities_full = get_audio_intensity_segments(audio_path, beat_times_full)
        
        # Map to segment beats
        intensities = []
        for i in range(len(beat_times) - 1):
            beat_start_abs = beat_times[i] + segment_info['start_time']
            # Find corresponding intensity in full audio
            for j, bt in enumerate(beat_times_full[:-1]):
                if abs(bt - beat_start_abs) < 0.1:  # Match within 100ms
                    if j < len(intensities_full):
                        intensities.append(intensities_full[j])
                    break
        
        if not intensities or len(intensities) < len(beat_times) - 1:
            intensities = [0.5] * (len(beat_times) - 1)
        
        # STEP 3: Classify clips by emotion
        print("Classifying clips...")
        clip_classifications = classify_multiple_clips(video_paths)
        
        # STEP 4: Match clips to beats based on PROGRESSIVE intensity
        print("Matching clips to beats with progressive intensity...")
        
        # Sort clips by intensity (for matching)
        sorted_clips_high = sorted(
            clip_classifications.items(),
            key=lambda x: x[1]['intensity'],
            reverse=True
        )
        sorted_clips_low = sorted(
            clip_classifications.items(),
            key=lambda x: x[1]['intensity']
        )
        
        clips = []
        
        # Calculate calm end relative to segment
        calm_end_relative = segment_info['calm_end'] - segment_info['start_time']
        
        for i in range(len(beat_times) - 1):
            if i >= len(intensities):
                break
            
            beat_start = beat_times[i]
            beat_end = beat_times[i + 1]
            segment_duration = beat_end - beat_start
            
            # PROGRESSIVE INTENSITY: Use segment's calm_end timestamp
            audio_intensity = intensities[i]
            
            # Before calm_end = calm clips, after = rage clips
            if beat_start < calm_end_relative:
                # Intro/buildup: prefer calm clips
                intensity_threshold = 0.7
            else:
                # Drop/rage part: prefer rage clips
                intensity_threshold = 0.3
            
            # Match based on combined criteria
            if audio_intensity > intensity_threshold:
                # Epic/Rage clips
                candidate_clips = sorted_clips_high
            else:
                # Calm/Sad clips
                candidate_clips = sorted_clips_low
            
            # Cycle through clips evenly
            selected_path = candidate_clips[i % len(candidate_clips)][0]
            
            try:
                video = VideoFileClip(selected_path)
                
                # IMPROVED CROPPING: Less aggressive, better visibility
                target_ratio = 9/16
                current_ratio = video.w / video.h
                
                # Calculate crop with some margin to avoid cutting off subjects
                if current_ratio > target_ratio:
                    # Too wide: crop width but keep slightly wider for safety
                    new_width = video.h * target_ratio * 1.1  # 10% extra width
                    if new_width > video.w:
                        new_width = video.w
                    center_x = video.w / 2
                    video = video.cropped(x1=center_x - new_width/2, width=new_width, height=video.h)
                else:
                    # Too tall: crop height
                    new_height = video.w / target_ratio * 0.9  # Slightly less aggressive
                    if new_height > video.h:
                        new_height = video.h
                    center_y = video.h / 2
                    video = video.cropped(y1=center_y - new_height/2, width=video.w, height=new_height)
                
                # Resize to standard resolution (720 width for 9:16)
                video = video.resized(width=720)
                
                # Cut clip to match beat duration - FIXED: ensure proper clip extraction
                if video.duration > segment_duration + 0.1:  # Add small buffer
                    # Pick random start point with enough room
                    max_start = video.duration - segment_duration
                    if max_start > 0:
                        start_point = random.uniform(0, max_start)
                        segment = video.subclipped(start_point, start_point + segment_duration)
                    else:
                        segment = video.subclipped(0, min(segment_duration, video.duration))
                else:
                    # Video is shorter than segment, loop or extend
                    if video.duration < segment_duration:
                        # Loop the clip to fill duration
                        num_loops = int(np.ceil(segment_duration / video.duration))
                        looped = concatenate_videoclips([video] * num_loops)
                        segment = looped.subclipped(0, segment_duration)
                    else:
                        segment = video.subclipped(0, segment_duration)
                
                # BEAT-SYNCED FLASH EFFECTS
                # Quick zoom pulse and brightness flash on beat
                def beat_flash_effect(get_frame, t):
                    """
                    Apply quick zoom pulse and brightness flash at beat hits.
                    """
                    frame = get_frame(t)
                    
                    # Check if we're near a beat (within 0.1s)
                    time_in_clip = t
                    near_beat = False
                    for beat in beat_times:
                        if abs((beat_start + time_in_clip) - beat) < 0.1:
                            near_beat = True
                            break
                    
                    if near_beat:
                        # Quick brightness flash (increase brightness by 30%)
                        frame = np.clip(frame * 1.3, 0, 255).astype(np.uint8)
                    
                    return frame
                
                # Apply flash effect
                segment = segment.transform(beat_flash_effect)
                
                # Quick zoom pulse: 1.0x -> 1.05x -> 1.0x during clip
                def zoom_pulse(t):
                    progress = t / segment.duration if segment.duration > 0 else 0
                    # Sine wave for pulse effect
                    scale = 1.0 + 0.05 * abs(np.sin(progress * np.pi * 2))
                    return scale
                
                segment = segment.resized(lambda t: zoom_pulse(t))
                
                # Add crossfade transition
                if i == 0:
                    # First clip: fade in BOTH video and brightness
                    segment = segment.with_effects([vfx.FadeIn(0.3)])
                else:
                    # Other clips: crossfade
                    segment = segment.with_effects([vfx.CrossFadeIn(0.2)])
                
                # Last clip: fade out BOTH video and brightness
                if i == len(beat_times) - 2:
                    segment = segment.with_effects([vfx.FadeOut(0.3)])
                
                clips.append(segment)
                
            except Exception as e:
                print(f"Error processing {selected_path}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if not clips:
            print("No clips created.")
            return None
        
        # Concatenate clips
        print("Concatenating clips...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Ensure final video matches audio duration exactly
        if final_video.duration > audio_duration:
            final_video = final_video.subclipped(0, audio_duration)
        elif final_video.duration < audio_duration:
            # Extend if needed (shouldn't happen, but safety check)
            print(f"Warning: video shorter than audio ({final_video.duration} vs {audio_duration})")
        
        # Set audio
        final_video = final_video.with_audio(audio)
        
        # Write output
        print("Rendering final video...")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        # Close all clips to free memory
        for clip in clips:
            clip.close()
        audio.close()
        final_video.close()
        
        return output_path

    except Exception as e:
        print(f"Error creating edit: {e}")
        import traceback
        traceback.print_exc()
        return None
