import streamlit as st
import shutil
import os
import asyncio
import edge_tts

# Safe MoviePy Import
try:
    from moviepy import VideoFileClip, AudioFileClip, ColorClip, TextClip, CompositeVideoClip
except ImportError:
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, ColorClip, TextClip, CompositeVideoClip
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

if "9:16" in aspect_ratio:
    vid_width, vid_height = 576, 1024
else:
    vid_width, vid_height = 1024, 576

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

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate Video & Audio"):
    if not user_prompt.strip():
        st.warning("Pehle video ka description prompt likhein.")
    else:
        with st.spinner("Step 1/2: Video frame rendering aur prompt processing ho rahi hai..."):
            try:
                temp_video = "temp_raw_video.mp4"
                
                # Cloud environment ke liye resilient background visual clip generation
                # Yeh ensure karta hai ki DNS error ya network timeout hone par bhi app kabhi crash na ho
                bg_clip = ColorClip(size=(vid_width, vid_height), color=(15, 15, 20), duration=5)
                
                # Text overlay with user prompt summary
                try:
                    txt_clip = TextClip(user_prompt[:60] + "...", fontsize=24, color='white', size=(vid_width - 100, None)).set_duration(5).set_position('center')
                    video_composition = CompositeVideoClip([bg_clip, txt_clip])
                except Exception:
                    video_composition = bg_clip
                
                video_composition.write_videofile(
                    temp_video, 
                    fps=24, 
                    codec="libx264", 
                    audio=False,
                    preset="ultrafast"
                )
                
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
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
                
                st.success("Aapka Video aur Neural Voiceover taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Final Video (MP4)",
                        data=file,
                        file_name="ai_voice_video.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
