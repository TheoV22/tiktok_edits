"""
Executor Agent - Performs video editing based on orchestrator's plan.
"""
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx, afx
import numpy as np
import os
import random

def execute_editing_plan(plan: dict, audio_path: str, video_paths: list[str], output_path: str) -> str:
    """
    Executor agent that creates the final video based on orchestrator's plan.
    
    Args:
        plan: Editing plan from orchestrator
        audio_path: Path to audio file
        video_paths: List of available video clips
        output_path: Output file path
    
    Returns:
        Path to created video or None if failed
    """
    print("\n=== Executor Agent: Building Video ===")
    
    try:
        # Load audio with segment selection
        audio_full = AudioFileClip(audio_path)
        segment = plan['audio_segment']
        audio = audio_full.subclipped(segment['start'], segment['end'])
        
        # Get fade duration from plan
        fade_duration = plan.get('fade_duration', 0.5)
        
        # Apply AUDIO fades (smooth volume reduction)
        audio = audio.with_effects([
            afx.AudioFadeIn(fade_duration),
            afx.AudioFadeOut(fade_duration)
        ])
        
        beat_times = plan['beat_times']
        beat_assignments = plan['beat_assignments']
        clip_classifications = plan['clip_classifications']
        
        # Sort clips by intensity
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
        
        for assignment in beat_assignments:
            i = assignment['beat_idx']
            if i >= len(beat_times) - 1:
                break
            
            beat_start = beat_times[i]
            beat_end = beat_times[i + 1]
            segment_duration = beat_end - beat_start
            clip_type = assignment['clip_type']
            effects = assignment['effects']
            
            # Select clip based on type
            if clip_type == "rage":
                candidate_clips = sorted_clips_high
            elif clip_type == "calm":
                candidate_clips = sorted_clips_low
            else:  # mixed
                candidate_clips = list(clip_classifications.items())
            
            selected_path = candidate_clips[i % len(candidate_clips)][0]
            
            try:
                video = VideoFileClip(selected_path)
                
                # Crop to 9:16
                target_ratio = 9/16
                current_ratio = video.w / video.h
                
                if current_ratio > target_ratio:
                    new_width = video.h * target_ratio * 1.1
                    if new_width > video.w:
                        new_width = video.w
                    center_x = video.w / 2
                    video = video.cropped(x1=center_x - new_width/2, width=new_width, height=video.h)
                else:
                    new_height = video.w / target_ratio * 0.9
                    if new_height > video.h:
                        new_height = video.h
                    center_y = video.h / 2
                    video = video.cropped(y1=center_y - new_height/2, width=video.w, height=new_height)
                
                video = video.resized(width=720)
                
                # Cut to duration
                if video.duration > segment_duration + 0.1:
                    max_start = video.duration - segment_duration
                    if max_start > 0:
                        start_point = random.uniform(0, max_start)
                        segment = video.subclipped(start_point, start_point + segment_duration)
                    else:
                        segment = video.subclipped(0, min(segment_duration, video.duration))
                else:
                    if video.duration < segment_duration:
                        num_loops = int(np.ceil(segment_duration / video.duration))
                        looped = concatenate_videoclips([video] * num_loops)
                        segment = looped.subclipped(0, segment_duration)
                    else:
                        segment = video.subclipped(0, segment_duration)
                
                # Apply effects from plan (except fades - those go on final video)
                for effect in effects:
                    effect_type = effect['type'] if isinstance(effect, dict) else effect
                    
                    if effect_type == "flash":
                        def beat_flash_effect(get_frame, t):
                            frame = get_frame(t)
                            time_in_clip = t
                            near_beat = False
                            for beat in beat_times:
                                if abs((beat_start + time_in_clip) - beat) < 0.1:
                                    near_beat = True
                                    break
                            if near_beat:
                                frame = np.clip(frame * 1.3, 0, 255).astype(np.uint8)
                            return frame
                        segment = segment.transform(beat_flash_effect)
                    
                    elif effect_type == "zoom_pulse":
                        def zoom_pulse(t):
                            progress = t / segment.duration if segment.duration > 0 else 0
                            scale = 1.0 + 0.05 * abs(np.sin(progress * np.pi * 2))
                            return scale
                        segment = segment.resized(lambda t: zoom_pulse(t))
                    
                    # Skip fade_in and fade_out - they're applied to final video
                
                # Crossfade between clips for smooth transitions
                if i > 0:
                    segment = segment.with_effects([vfx.CrossFadeIn(0.2)])
                
                clips.append(segment)
                
            except Exception as e:
                print(f"Error processing {selected_path}: {e}")
                continue
        
        if not clips:
            print("No clips created.")
            return None
        
        # Concatenate
        print("Concatenating clips...")
        final_video = concatenate_videoclips(clips, method="compose")
        
        # CRITICAL FIX: Ensure video duration EXACTLY matches audio duration
        audio_duration = audio.duration
        video_duration = final_video.duration
        
        print(f"Video duration: {video_duration:.2f}s, Audio duration: {audio_duration:.2f}s")
        
        if abs(video_duration - audio_duration) > 0.1:
            print(f"⚠️  Duration mismatch detected! Adjusting video...")
            
            if video_duration < audio_duration:
                # Video is shorter - loop it to fill audio duration
                print(f"Looping video to match audio duration...")
                num_loops = int(np.ceil(audio_duration / video_duration))
                looped_video = concatenate_videoclips([final_video] * num_loops, method="compose")
                final_video = looped_video.subclipped(0, audio_duration)
            else:
                # Video is longer - trim it
                print(f"Trimming video to match audio duration...")
                final_video = final_video.subclipped(0, audio_duration)
        
        # Apply fade effects to FINAL video (not individual clips) to avoid freezing
        print(f"Applying fade effects ({fade_duration}s)...")
        final_video = final_video.with_effects([
            vfx.FadeIn(fade_duration),
            vfx.FadeOut(fade_duration)
        ])
        
        # Set audio
        final_video = final_video.with_audio(audio)
        
        print(f"✅ Final video duration: {final_video.duration:.2f}s (matches audio)")
        
        # Render
        print("Rendering final video...")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        # Cleanup
        for clip in clips:
            clip.close()
        audio.close()
        final_video.close()
        
        print(f"✅ Video created: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error in executor: {e}")
        import traceback
        traceback.print_exc()
        return None
