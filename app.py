import streamlit as st
import requests
import os
import asyncio
import edge_tts
import urllib.parse
from PIL import Image as PILImage
import numpy as np

# Safe MoviePy Import (v1 & v2 compatible)
try:
    from moviepy import VideoFileClip, AudioFileClip, ImageClip
except ImportError:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip

st.set_page_config(page_title="Hinglish to Real Live-Action Reel Generator", layout="centered")
st.title("Hinglish to Real Reel Generator")
st.write("Hinglish prompt likhein, aur tool khud real live-action character, scene aur voiceover video taiyar kar dega.")

# 1. Format Selection (Reels by default)
aspect_ratio = st.selectbox(
    "Video Format Chunein:",
    ["9:16 (Instagram Reels / YouTube Shorts)", "16:9 (Landscape / Website)"]
)

if "9:16" in aspect_ratio:
    vid_width, vid_height = 576, 1024
else:
    vid_width, vid_height = 1024, 576

# 2. Hinglish Prompt Input
user_prompt = st.text_area(
    "Apna Prompt Hinglish ya English mein likhein:",
    placeholder="Jaise: ek handsome Indian boy New Delhi ki street par evening light mein chal raha hai, candid expression"
)

# 3. Voiceover & Character Settings
gender_choice = st.selectbox(
    "Character kiska hoga?",
    ["Real Indian Young Woman (Female)", "Real Indian Young Man (Male)", "Sirf Location / Scene (No Person)"]
)

voice_text = st.text_area(
    "Voiceover ke liye script likhein (Jo video mein boli jayegi):",
    placeholder="Zindagi ke safar mein aksar wahi log aage badhte hain jo rukna nahi jaante..."
)

# Voice Model Selection based on Gender
if "Female" in gender_choice:
    voice_options = {
        "hi-IN-SwaraNeural (Hindi Female - Natural & Expressive)": "hi-IN-SwaraNeural",
        "en-IN-NeerjaNeural (Indian Female - Warm & Realistic)": "en-IN-NeerjaNeural"
    }
else:
    voice_options = {
        "hi-IN-MadhurNeural (Hindi Male - Deep & Natural)": "hi-IN-MadhurNeural",
        "en-IN-PrabhatNeural (Indian Male - Authoritative & Clear)": "en-IN-PrabhatNeural"
    }

selected_voice_key = list(voice_options.values()[0]) if isinstance(voice_options, dict) else "hi-IN-SwaraNeural"
chosen_label = st.selectbox("Neural Voice Model Chunein:", list(voice_options.keys()))
selected_voice_key = voice_options[chosen_label]

# Strict Real Live-Action Booster (To avoid cartoon/animation)
LIVE_ACTION_BOOST = (
    ", real live-action documentary footage, shot on 35mm lens, f/1.8 aperture, "
    "authentic human skin texture, natural pores, candid facial expressions, realistic ambient lighting, "
    "real-world environment, zero cgi, zero animation, 8k resolution, photorealistic"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate Real Reel Video"):
    if not user_prompt.strip():
        st.warning("Kripya video ka prompt zaroor likhein.")
    elif not voice_text.strip():
        st.warning("Kripya voiceover script zaroor likhein.")
    else:
        # Automatically structure the user's Hinglish prompt into a professional cinematic prompt
        base_subject = ""
        if "Female" in gender_choice:
            base_subject = "A candid portrait of a real Indian young woman, "
        elif "Male" in gender_choice:
            base_subject = "A candid portrait of a real Indian young man, "
        else:
            base_subject = "A realistic raw documentary video frame of "
            
        final_prompt = f"{base_subject}{user_prompt.strip()}{LIVE_ACTION_BOOST}"
        
        # Step 1: Generate Neural Audio and Calculate Exact Duration
        audio_path = None
        target_duration = 6.0
        
        with st.spinner("Step 1/3: Natural neural voiceover generate ho raha hai..."):
            try:
                audio_path = "temp_neural_voice.mp3"
                asyncio.run(generate_edge_tts(voice_text, selected_voice_key, audio_path))
                
                if os.path.exists(audio_path):
                    temp_audio_clip = AudioFileClip(audio_path)
                    target_duration = min(temp_audio_clip.duration + 0.5, 30.0) # Match exact audio duration
                    temp_audio_clip.close()
            except Exception as e:
                st.error(f"Voice generation error: {e}")
                st.stop()

        # Step 2: Generate Real Live-Action Visual Frame
        with st.spinner("Step 2/3: Real live-action visual & camera motion render ho rahi hai..."):
            try:
                encoded_prompt = urllib.parse.quote(final_prompt)
                img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux-realism&nologo=true"
                
                response = requests.get(img_url, timeout=90)
                if response.status_code == 200 and len(response.content) > 1000:
                    img_path = "temp_reel_frame.jpg"
                    with open(img_path, "wb") as f:
                        f.write(response.content)
                else:
                    st.error("Visual generation fail ho gaya. Dobara click karein.")
                    st.stop()
                
                temp_video = "temp_raw_reel_video.mp4"
                
                try:
                    img_clip = ImageClip(img_path, duration=target_duration)
                except TypeError:
                    img_clip = ImageClip(img_path).set_duration(target_duration)
                
                # Smooth documentary camera push-in motion
                def reel_camera_motion(get_frame, t):
                    frame = get_frame(t)
                    h, w, _ = frame.shape
                    progress = t / target_duration
                    zoom_factor = 1.01 + (0.025 * progress)
                    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                    
                    y1 = (h - new_h) // 2
                    x1 = (w - new_w) // 2
                    
                    cropped = frame[y1:y1+new_h, x1:x1+new_w]
                    pil_img = PILImage.fromarray(cropped).resize((w, h), PILImage.Resampling.LANCZOS)
                    return np.array(pil_img)

                if hasattr(img_clip, "transform"):
                    animated_clip = img_clip.transform(reel_camera_motion)
                else:
                    animated_clip = img_clip.fl(reel_camera_motion, keep_duration=True)

                animated_clip.write_videofile(
                    temp_video, 
                    fps=24, 
                    codec="libx264", 
                    audio=False,
                    preset="medium"
                )
                
            except requests.exceptions.Timeout:
                st.error("Server timeout ho gaya. Dobara Generate button dabayein.")
                st.stop()
            except Exception as e:
                st.error(f"Video rendering error: {e}")
                st.stop()

        # Step 3: Merge Audio & Video Perfectly
        with st.spinner("Step 3/3: Voiceover aur Video ko sync karke final reel ban rahi hai..."):
            try:
                video_clip = VideoFileClip(temp_video)
                
                if audio_path and os.path.exists(audio_path):
                    audio_clip = AudioFileClip(audio_path)
                    if audio_clip.duration > video_clip.duration:
                        if hasattr(audio_clip, "subclipped"):
                            audio_clip = audio_clip.subclipped(0, video_clip.duration)
                        else:
                            audio_clip = audio_clip.subclip(0, video_clip.duration)
                            
                    if hasattr(video_clip, "with_audio"):
                        final_clip = video_clip.with_audio(audio_clip)
                    else:
                        final_clip = video_clip.set_audio(audio_clip)
                else:
                    final_clip = video_clip

                final_output_file = "instagram_reel_output.mp4"
                final_clip.write_videofile(
                    final_output_file, 
                    codec="libx264", 
                    audio_codec="aac", 
                    fps=24,
                    preset="medium"
                )
                
                video_clip.close()
                if os.path.exists(temp_video):
                    os.remove(temp_video)
                if os.path.exists(img_path):
                    os.remove(img_path)
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                
                st.success("Aapki Instagram Reel taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Reel (MP4)",
                        data=file,
                        file_name="my_ai_reel.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
