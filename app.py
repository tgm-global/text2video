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

st.set_page_config(page_title="AI 3D Cinematic Animation & Voice Generator", layout="centered")
st.title("AI 3D Cinematic Animation Generator")
st.write("Text prompt se high-end 3D animated character aur natural neural voiceover wala video taiyar karein.")

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
    "3D Character Kaun hoga?",
    [
        "Stylish Indian Young Woman (3D Animated Character)",
        "Stylish Indian Young Man (3D Animated Character)",
        "Custom Scene / Object (Koi character nahi, sirf scene)"
    ]
)

# 3. Scene & Action Prompt
user_prompt = st.text_area(
    "Scene aur action ka description likhein (Simple English):",
    placeholder="Standing in a futuristic neon-lit Mumbai street at night, smiling, expressive eyes, hand gesture"
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
        placeholder="Zindagi ke har mod par ek nayi kahani shuru hoti hai..."
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

# Character Base Setup
if "Woman" in gender_choice:
    base_subject = "A charismatic 3D animated Indian young woman speaking expressively, "
elif "Man" in gender_choice:
    base_subject = "A charismatic 3D animated Indian young man speaking expressively, "
else:
    base_subject = ""

# High-End 3D Realistic Animation Prompt Boost
ANIMATION_3D_BOOST = (
    ", stunning 3D cinematic animation, Unreal Engine 5 render, Pixar and Disney high-end 3D movie style, "
    "octane render, volumetric cinematic lighting, ray tracing, ultra-detailed textures, "
    "expressive face and eyes, vibrant rich colors, shallow depth of field, 8k resolution, masterpiece"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate 3D Animated Video"):
    if not user_prompt.strip():
        st.warning("Pehle scene ka description likhein.")
    elif "Neural" in audio_choice and not voice_text.strip():
        st.warning("Voiceover ke liye kuch text likhein.")
    else:
        final_prompt = f"{base_subject}{user_prompt.strip()}{ANIMATION_3D_BOOST}"
        
        # Step 1: Pehle Audio taiyar karte hain taaki video ki exact length pata chal sake
        audio_path = None
        target_duration = 6.0  # Default duration agar audio na ho
        
        with st.spinner("Step 1/3: Neural Voiceover / Audio process ho raha hai..."):
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
                    # Video ko audio se 0.5 second lamba rakhenge taaki end mein achanak na kate
                    target_duration = min(temp_audio_clip.duration + 0.5, 30.0) # Max 30 sec limit for fast cloud rendering
                    temp_audio_clip.close()
            except Exception as e:
                st.error(f"Audio processing error: {e}")
                st.stop()

        # Step 2: 3D Cinematic Visual Render
        with st.spinner("Step 2/3: 3D Cinematic Character & Scene render ho raha hai..."):
            try:
                encoded_prompt = urllib.parse.quote(final_prompt)
                img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux&nologo=true"
                
                response = requests.get(img_url, timeout=90)
                if response.status_code == 200 and len(response.content) > 1000:
                    img_path = "temp_3d_frame.jpg"
                    with open(img_path, "wb") as f:
                        f.write(response.content)
                else:
                    st.error("3D visual generation fail ho gaya. Dobara try karein.")
                    st.stop()
                
                temp_video = "temp_raw_3d_video.mp4"
                
                try:
                    img_clip = ImageClip(img_path, duration=target_duration)
                except TypeError:
                    img_clip = ImageClip(img_path).set_duration(target_duration)
                
                # Smooth 3D Camera Pan & Breathing Zoom Effect
                def cinematic_3d_camera(get_frame, t):
                    frame = get_frame(t)
                    h, w, _ = frame.shape
                    # Smooth progressive zoom + gentle floating camera sway
                    progress = t / target_duration
                    zoom_factor = 1.03 + (0.05 * progress) + (0.01 * np.sin(t * 2.5))
                    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                    
                    # Gentle horizontal & vertical camera drift
                    max_y_offset = (h - new_h) // 2
                    max_x_offset = (w - new_w) // 2
                    
                    y1 = int(max_y_offset + (max_y_offset * 0.3 * np.sin(t * 1.5)))
                    x1 = int(max_x_offset + (max_x_offset * 0.3 * np.cos(t * 1.2)))
                    
                    y1 = max(0, min(y1, h - new_h))
                    x1 = max(0, min(x1, w - new_w))
                    
                    cropped = frame[y1:y1+new_h, x1:x1+new_w]
                    pil_img = PILImage.fromarray(cropped).resize((w, h), PILImage.Resampling.LANCZOS)
                    return np.array(pil_img)

                if hasattr(img_clip, "transform"):
                    animated_clip = img_clip.transform(cinematic_3d_camera)
                else:
                    animated_clip = img_clip.fl(cinematic_3d_camera, keep_duration=True)

                animated_clip.write_videofile(
                    temp_video, 
                    fps=24, 
                    codec="libx264", 
                    audio=False,
                    preset="medium"
                )
                
            except requests.exceptions.Timeout:
                st.error("Server par load zyada hone ki wajah se timeout ho gaya. Ek baar phir click karein.")
                st.stop()
            except Exception as e:
                st.error(f"3D Rendering error: {e}")
                st.stop()

        # Step 3: Final Video & Audio Sync
        with st.spinner("Step 3/3: Final 3D Video aur Audio merge ho rahe hain..."):
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

                final_output_file = "final_3d_animated_video.mp4"
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
                
                st.success("Aapka 3D Cinematic Animated Video taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download 3D Video (MP4)",
                        data=file,
                        file_name="3d_cinematic_video.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
