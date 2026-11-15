import streamlit as st
from gradio_client import Client
import shutil
import os
import asyncio
import edge_tts

# Safe MoviePy Import
try:
    from moviepy import VideoFileClip, AudioFileClip
except ImportError:
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
    except ImportError:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip

st.set_page_config(page_title="AI Realistic Video & Neural Voice Generator", layout="centered")
st.title("AI Realistic Video Generator")
st.write("Text prompt se realistic video aur natural neural voiceover taiyar karein.")

# 1. Format Selection
aspect_ratio = st.selectbox(
    "Video Format Chunein:",
    ["9:16 (Instagram Reels / YouTube Shorts)", "16:9 (Landscape / Website)"]
)

# 2. Text Prompt for Video
user_prompt = st.text_area(
    "Video ka description prompt likhein (Simple English):",
    placeholder="A romantic couple standing under streetlights on a foggy night, cinematic lighting, photorealistic"
)

# 3. Audio & Neural Voice Options
audio_choice = st.radio(
    "Audio ke liye aap kya use karna chahte hain?",
    ["Neural AI Voiceover (100% Non-Robotic & Natural)", "Apna khud ka Song/Music upload karein (.mp3)"]
)

voice_text = ""
selected_voice_key = "en-US-AriaNeural (Female - Professional & Natural)"

if "Neural" in audio_choice:
    voice_text = st.text_input(
        "Voiceover ke liye text likhein:",
        placeholder="Raat ka yeh silsila bhi kya khubsurat hai..."
    )
    
    voice_options = {
        "en-US-AriaNeural (Female - Professional & Natural)": "en-US-AriaNeural",
        "en-US-GuyNeural (Male - Deep & Clear)": "en-US-GuyNeural",
        "en-IN-NeerjaNeural (Indian Female - Warm & Realistic)": "en-IN-NeerjaNeural",
        "en-IN-PrabhatNeural (Indian Male - Authoritative & Clear)": "en-IN-PrabhatNeural",
        "en-GB-SoniaNeural (British Female - Soft & Elegant)": "en-GB-SoniaNeural",
        "en-GB-RyanNeural (British Male - Young & Energetic)": "en-GB-RyanNeural"
    }
    
    chosen_label = st.selectbox("Ultra-Realistic Voice Model Chunein:", list(voice_options.keys()))
    selected_voice_key = voice_options[chosen_label]
else:
    uploaded_audio = st.file_uploader("Apni Background .mp3 audio file upload karein", type=["mp3", "wav"])

REALISM_BOOST = (
    ", photorealistic, real life raw footage, shot on 35mm lens, "
    "natural human skin texture, realistic lighting, ultra detailed, "
    "8k resolution, live action film, natural motion, cinematic"
)

STRICT_NEGATIVE_PROMPT = (
    "animated, cartoon, anime, 3d render, cgi, illustration, painting, "
    "drawing, artificial, plastic skin, distorted face, extra fingers, "
    "blurry, low quality, watermark, text, glitch, uncanny valley"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate Video & Audio"):
    if not user_prompt.strip():
        st.warning("Pehle video ka description prompt likhein.")
    else:
        final_prompt = user_prompt.strip() + REALISM_BOOST
        
        with st.spinner("Step 1/2: AI realistic video generate ho raha hai (1-2 min lag sakte hain)..."):
            try:
                # Stable video generation client without any image dependencies
                client = Client("stabilityai/stable-video-diffusion")
                
                result = client.predict(
                    prompt=final_prompt,
                    negative_prompt=STRICT_NEGATIVE_PROMPT,
                    api_name="/predict"
                )
                
                raw_video_path = result[0] if isinstance(result, (list, tuple)) else result
                temp_video = "temp_raw_video.mp4"
                shutil.copy(raw_video_path, temp_video)
                
            except Exception as e:
                # Fallback to alternative stable public endpoint if primary is busy
                try:
                    client = Client("cerspense/zeroscope_v2_5x")
                    result = client.predict(
                        prompt=final_prompt,
                        api_name="/predict"
                    )
                    raw_video_path = result[0] if isinstance(result, (list, tuple)) else result
                    temp_video = "temp_raw_video.mp4"
                    shutil.copy(raw_video_path, temp_video)
                except Exception as inner_e:
                    st.error(f"Video generation error: {inner_e}")
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
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                
                st.success("Aapka Realistic Video taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Final Video (MP4)",
                        data=file,
                        file_name="realistic_ai_video.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
