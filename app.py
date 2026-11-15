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

st.set_page_config(page_title="AI Real Live-Action Video & Voice Generator", layout="centered")
st.title("AI Real Live-Action Video Generator")
st.write("Text prompt se ekdam asli live-action footage aur natural neural voiceover taiyar karein.")

# 1. Format Selection
aspect_ratio = st.selectbox(
    "Video Format Chunein:",
    ["9:16 (Instagram Reels / YouTube Shorts)", "16:9 (Landscape / Website)"]
)

if "9:16" in aspect_ratio:
    vid_width, vid_height = 576, 1024
else:
    vid_width, vid_height = 1024, 576

# 2. Character Selection
gender_choice = st.selectbox(
    "Subject Kaun hai?",
    [
        "Real Indian Young Woman (Live-Action)",
        "Real Indian Young Man (Live-Action)",
        "Real Location / Street / Nature Scene (No Person)"
    ]
)

# 3. Scene Prompt
user_prompt = st.text_area(
    "Scene ka description likhein (Simple English):",
    placeholder="Walking on a bustling Delhi street during evening time, natural expressions, candid shot"
)

# 4. Audio & Neural Voice Options
audio_choice = st.radio(
    "Audio ke liye aap kya use karna chahte hain?",
    ["Neural AI Voiceover (100% Non-Robotic & Natural)", "Apna khud ka Song/Music upload karein (.mp3)"]
)

voice_text = ""
selected_voice_key = "hi-IN-SwaraNeural"

if "Neural" in audio_choice:
    voice_text = st.text_input(
        "Voiceover ke liye text likhein:",
        placeholder="Zindagi ke safar mein aksar aisa hota hai..."
    )
    
    if "Man" in gender_choice:
        voice_options = {
            "hi-IN-MadhurNeural (Hindi Male - Deep & Natural)": "hi-IN-MadhurNeural",
            "en-IN-PrabhatNeural (Indian Male - Authoritative & Clear)": "en-IN-PrabhatNeural",
            "en-US-GuyNeural (US Male - Deep)": "en-US-GuyNeural"
        }
    else:
        voice_options = {
            "hi-IN-SwaraNeural (Hindi Female - Natural & Expressive)": "hi-IN-SwaraNeural",
            "en-IN-NeerjaNeural (Indian Female - Warm & Realistic)": "en-IN-NeerjaNeural",
            "en-US-AriaNeural (US Female - Professional)": "en-US-AriaNeural"
        }
    
    chosen_label = st.selectbox("Voice Model Chunein:", list(voice_options.keys()))
    selected_voice_key = voice_options[chosen_label]
else:
    uploaded_audio = st.file_uploader("Apni Background .mp3 audio file upload karein", type=["mp3", "wav"])

# Subject Prefix
if "Woman" in gender_choice:
    base_subject = "A candid portrait of a real Indian young woman, "
elif "Man" in gender_choice:
    base_subject = "A candid portrait of a real Indian young man, "
else:
    base_subject = "A realistic raw video frame of "

# Strict Real Live-Action Footage Prompt (No 3D, No Movie Style)
LIVE_ACTION_BOOST = (
    ", real live-action footage, documentary style, shot on 35mm lens, f/1.8 aperture, "
    "natural human skin texture, pores, candid facial expressions, realistic ambient lighting, "
    "real-world environment, zero cgi, zero animation, zero illustration, 8k resolution, photorealistic"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate Real Live-Action Video"):
    if not user_prompt.strip():
        st.warning("Pehle scene ka description likhein.")
    elif "Neural" in audio_choice and not voice_text.strip():
        st.warning("Voiceover ke liye kuch text likhein.")
    else:
        final_prompt = f"{base_subject}{user_prompt.strip()}{LIVE_ACTION_BOOST}"
        
        # Step 1: Audio Duration Check
        audio_path = None
        target_duration = 6.0
        
        with st.spinner("Step 1/3: Audio process ho rahi hai..."):
            try:
                if "Neural" in audio_choice and voice_text.strip():
                    audio_path = "temp_neural_voice.mp3"
                    asyncio.run(generate_edge_tts(voice_text, selected_voice_key, audio_path))
                elif "upload" in audio_choice and 'uploaded_audio' in locals() and uploaded_audio is not None:
                    audio_path = "temp_uploaded_audio.mp3"
                    with open(audio_path, "wb") as f:
                        f.write(uploaded_audio.getbuffer())
                
                if audio_path and os.path.exists(audio_path):
                    temp_audio_clip = AudioFileClip(audio_path)
                    target_duration = min(temp_audio_clip.duration + 0.5, 30.0)
                    temp_audio_clip.close()
            except Exception as e:
                st.error(f"Audio processing error: {e}")
                st.stop()

        # Step 2: Real Live-Action Visual Render
        with st.spinner("Step 2/3: Real live-action photograph render ho rahi hai..."):
            try:
                encoded_prompt = urllib.parse.quote(final_prompt)
                img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux-realism&nologo=true"
                
                response = requests.get(img_url, timeout=90)
                if response.status_code == 200 and len(response.content) > 1000:
                    img_path = "temp_live_frame.jpg"
                    with open(img_path, "wb") as f:
                        f.write(response.content)
                else:
                    st.error("Visual generation fail ho gaya. Dobara try karein.")
                    st.stop()
                
                temp_video = "temp_raw_live_video.mp4"
                
                try:
                    img_clip = ImageClip(img_path, duration=target_duration)
                except TypeError:
                    img_clip = ImageClip(img_path).set_duration(target_duration)
                
                # Subtle documentary camera movement
                def documentary_camera_motion(get_frame, t):
                    frame = get_frame(t)
                    h, w, _ = frame.shape
                    progress = t / target_duration
                    zoom_factor = 1.01 + (0.02 * progress) # Very subtle camera push-in like real documentary
                    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                    
                    max_y_offset = (h - new_h) // 2
                    max_x_offset = (w - new_w) // 2
                    
                    y1 = int(max_y_offset)
                    x1 = int(max_x_offset)
                    
                    cropped = frame[y1:y1+new_h, x1:x1+new_w]
                    pil_img = PILImage.fromarray(cropped).resize((w, h), PILImage.Resampling.LANCZOS)
                    return np.array(pil_img)

                if hasattr(img_clip, "transform"):
                    animated_clip = img_clip.transform(documentary_camera_motion)
                else:
                    animated_clip = img_clip.fl(documentary_camera_motion, keep_duration=True)

                animated_clip.write_videofile(
                    temp_video, 
                    fps=24, 
                    codec="libx264", 
                    audio=False,
                    preset="medium"
                )
                
            except requests.exceptions.Timeout:
                st.error("Server timeout ho gaya. Ek baar phir click karein.")
                st.stop()
            except Exception as e:
                st.error(f"Rendering error: {e}")
                st.stop()

        # Step 3: Final Video & Audio Sync
        with st.spinner("Step 3/3: Final Live-Action Video aur Audio merge ho rahe hain..."):
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

                final_output_file = "final_live_action_video.mp4"
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
                
                st.success("Aapka Real Live-Action Video taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Live-Action Video (MP4)",
                        data=file,
                        file_name="live_action_video.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
