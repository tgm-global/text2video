import streamlit as st
from gradio_client import Client
import shutil
import os
import asyncio
import edge_tts
from PIL import Image as PILImage

# Safe MoviePy Import for both old and new versions
try:
    from moviepy import VideoFileClip, AudioFileClip
except ImportError:
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
    except ImportError:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip

st.set_page_config(page_title="AI Smart Hybrid Video & Neural Voice Generator", layout="centered")
st.title("AI Smart Hybrid Realistic Video Generator")
st.write("Photo upload karein (optional) ya sirf text prompt dein—code automatic realistic video aur natural neural voiceover taiyar kar dega.")

aspect_ratio = st.selectbox(
    "Video Format Chunein:",
    ["9:16 (Instagram Reels / YouTube Shorts)", "16:9 (Landscape / Website)"]
)

if "9:16" in aspect_ratio:
    width, height = 512, 768
else:
    width, height = 768, 512

uploaded_image = st.file_uploader(
    "Apni Image Upload karein (Optional):",
    type=["jpg", "jpeg", "png"]
)

user_prompt = st.text_area(
    "Video ka description ya motion likhein (Simple English):",
    placeholder="A stylish person smiling and looking at the camera, cinematic lighting"
)

audio_choice = st.radio(
    "Audio ke liye aap kya use karna chahte hain?",
    ["Neural AI Voiceover (100% Non-Robotic & Natural)", "Apna khud ka Song/Music upload karein (.mp3)"]
)

voice_text = ""
selected_voice_key = "en-US-AriaNeural (Female - Professional & Natural)"

if "Neural" in audio_choice:
    voice_text = st.text_input(
        "Voiceover ke liye text likhein:",
        placeholder="Discover the newest collection today, click the link below!"
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

if st.button("Generate Smart Video & Audio"):
    if not user_prompt.strip():
        st.warning("Pehle video ka description / motion prompt likhein.")
    else:
        final_prompt = user_prompt.strip() + REALISM_BOOST
        
        with st.spinner("Step 1/2: AI realistic video generate ho raha hai..."):
            try:
                client = Client("Lightricks/ltx-video-distilled")
                
                if uploaded_image is not None:
                    img_path = "temp_input_image.png"
                    image_obj = PILImage.open(uploaded_image)
                    image_obj.save(img_path)
                    
                    result = client.predict(
                        image=img_path,
                        prompt=final_prompt,
                        negative_prompt=STRICT_NEGATIVE_PROMPT,
                        api_name="/image_to_video"
                    )
                else:
                    result = client.predict(
                        prompt=final_prompt,
                        negative_prompt=STRICT_NEGATIVE_PROMPT,
                        height=height,
                        width=width,
                        num_frames=49,
                        api_name="/text_to_video"
                    )
                
                raw_video_path = result[0] if isinstance(result, (list, tuple)) else result
                temp_video = "temp_raw_video.mp4"
                shutil.copy(raw_video_path, temp_video)
                
            except Exception as e:
                try:
                    result = client.predict(
                        prompt=final_prompt,
                        negative_prompt=STRICT_NEGATIVE_PROMPT,
                        height=height,
                        width=width,
                        num_frames=49,
                        api_name="/text_to_video"
                    )
                    raw_video_path = result[0] if isinstance(result, (list, tuple)) else result
                    temp_video = "temp_raw_video.mp4"
                    shutil.copy(raw_video_path, temp_video)
                except Exception as inner_e:
                    st.error(f"Video generation mein error aayi: {inner_e}")
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
                    
                    # Handle duration trimming based on available moviepy methods
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
                if 'img_path' in locals() and os.path.exists(img_path):
                    os.remove(img_path)
                
                st.success("Aapka Smart Realistic Video taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Final Video (MP4)",
                        data=file,
                        file_name="smart_hybrid_video.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
