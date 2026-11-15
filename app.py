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

st.set_page_config(page_title="AI Realistic Model Video & Neural Voice Generator", layout="centered")
st.title("AI Real-Life Model & Voice Generator")
st.write("Text prompt se ekdam photorealistic model aur natural neural voiceover taiyar karein.")

# 1. Format Selection
aspect_ratio = st.selectbox(
    "Video Format Chunein:",
    ["9:16 (Instagram Reels / YouTube Shorts)", "16:9 (Landscape / Website)"]
)

if "9:16" in aspect_ratio:
    vid_width, vid_height = 576, 1024
else:
    vid_width, vid_height = 1024, 576

# 2. Text Prompt for Realistic Model
user_prompt = st.text_area(
    "Video ka description likhein (Simple English):",
    placeholder="A stylish professional Indian model smiling and looking at the camera, natural outdoor lighting"
)

# 3. Audio & Neural Voice Options
audio_choice = st.radio(
    "Audio ke liye aap kya use karna chahte hain?",
    ["Neural AI Voiceover (100% Non-Robotic & Natural)", "Apna khud ka Song/Music upload karein (.mp3)"]
)

voice_text = ""
selected_voice_key = "en-IN-NeerjaNeural"

if "Neural" in audio_choice:
    voice_text = st.text_input(
        "Voiceover ke liye text likhein:",
        placeholder="Raat ka yeh silsila bhi kya khubsurat hai..."
    )
    
    voice_options = {
        "en-IN-NeerjaNeural (Indian Female - Warm & Realistic)": "en-IN-NeerjaNeural",
        "en-IN-PrabhatNeural (Indian Male - Authoritative & Clear)": "en-IN-PrabhatNeural",
        "hi-IN-SwaraNeural (Hindi Female - Natural & Expressive)": "hi-IN-SwaraNeural",
        "hi-IN-MadhurNeural (Hindi Male - Deep & Natural)": "hi-IN-MadhurNeural",
        "en-US-AriaNeural (US Female - Professional & Natural)": "en-US-AriaNeural",
        "en-US-GuyNeural (US Male - Deep & Clear)": "en-US-GuyNeural"
    }
    
    chosen_label = st.selectbox("Ultra-Realistic Voice Model Chunein:", list(voice_options.keys()))
    selected_voice_key = voice_options[chosen_label]
else:
    uploaded_audio = st.file_uploader("Apni Background .mp3 audio file upload karein", type=["mp3", "wav"])

REALISM_BOOST = (
    ", raw candid DSLR photo, shot on 35mm lens, f/1.8, "
    "natural human skin texture, visible pores, realistic lighting, "
    "live action photography, ultra detailed, no cgi, no 3d render, no illustration"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate Realistic Video & Audio"):
    if not user_prompt.strip():
        st.warning("Pehle video ka description prompt likhein.")
    else:
        final_prompt = user_prompt.strip() + REALISM_BOOST
        
        with st.spinner("Step 1/2: Photorealistic image ban rahi hai (40-60 seconds lag sakte hain)..."):
            try:
                encoded_prompt = urllib.parse.quote(final_prompt)
                img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux&nologo=true"
                
                # Timeout 90 seconds kar diya hai taaki server response ka pura wait kare
                response = requests.get(img_url, timeout=90)
                if response.status_code == 200 and len(response.content) > 1000:
                    img_path = "temp_model_image.jpg"
                    with open(img_path, "wb") as f:
                        f.write(response.content)
                else:
                    st.error(f"Server se image nahi mil paayi (Status: {response.status_code}). Ek baar phir try karein.")
                    st.stop()
                
                temp_video = "temp_raw_video.mp4"
                duration_sec = 5
                
                try:
                    img_clip = ImageClip(img_path, duration=duration_sec)
                except TypeError:
                    img_clip = ImageClip(img_path).set_duration(duration_sec)
                
                def zoom_effect(get_frame, t):
                    frame = get_frame(t)
                    h, w, _ = frame.shape
                    zoom_factor = 1.0 + (0.04 * (t / duration_sec))
                    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
                    y1, x1 = (h - new_h) // 2, (w - new_w) // 2
                    cropped = frame[y1:y1+new_h, x1:x1+new_w]
                    
                    pil_img = PILImage.fromarray(cropped).resize((w, h), PILImage.Resampling.LANCZOS)
                    return np.array(pil_img)

                # MoviePy v2 (.transform) aur v1 (.fl) dono ke liye safe handling
                if hasattr(img_clip, "transform"):
                    zoomed_clip = img_clip.transform(zoom_effect)
                else:
                    zoomed_clip = img_clip.fl(zoom_effect, keep_duration=True)

                zoomed_clip.write_videofile(
                    temp_video, 
                    fps=24, 
                    codec="libx264", 
                    audio=False,
                    preset="medium"
                )
                
            except requests.exceptions.Timeout:
                st.error("Server busy hone ki wajah se time out ho gaya. Dobara Generate button dabayein.")
                st.stop()
            except Exception as e:
                st.error(f"Video rendering error: {e}")
                st.stop()

        with st.spinner("Step 2/2: Audio/Voiceover merge kiya ja raha hai..."):
            try:
                video_clip = VideoFileClip(temp_video)
                audio_path = None
                
                if "Neural" in audio_choice and voice_text.strip():
                    audio_path = "temp_neural_voice.mp3"
                    asyncio.run(generate_edge_tts(voice_text, selected_voice_key, audio_path))
                
                elif "upload" in audio_choice and 'uploaded_audio' in locals() and uploaded_audio is not None:
                    audio_path = "temp_uploaded_audio.mp3"
                    with open(audio_path, "wb") as f:
                        f.write(uploaded_audio.getbuffer())

                if audio_path and os.path.exists(audio_path):
                    audio_clip = AudioFileClip(audio_path)
                    
                    if hasattr(audio_clip, "subclipped"):
                        if audio_clip.duration > video_clip.duration:
                            audio_clip = audio_clip.subclipped(0, video_clip.duration)
                    else:
                        if audio_clip.duration > video_clip.duration:
                            audio_clip = audio_clip.subclip(0, video_clip.duration)
                            
                    if hasattr(video_clip, "with_audio"):
                        final_clip = video_clip.with_audio(audio_clip)
                    else:
                        final_clip = video_clip.set_audio(audio_clip)
                else:
                    final_clip = video_clip

                final_output_file = "final_output_video.mp4"
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
                
                st.success("Aapka Photorealistic Model Video taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Final Video (MP4)",
                        data=file,
                        file_name="realistic_model_video.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
