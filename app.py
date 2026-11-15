import streamlit as st
import requests
import os
import asyncio
import edge_tts
import urllib.parse
import time

# Safe MoviePy Import (v1 & v2 compatible)
try:
    from moviepy import VideoFileClip, AudioFileClip, ImageClip
except ImportError:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip

st.set_page_config(page_title="Instagram Reel Generator (Auto-Retry HD)", layout="centered")
st.title("Instagram HD Reel Generator")
st.write("Hinglish prompt se clean HD image aur natural voiceover wali reel banayein.")

# 1. Format Selection (Reels 9:16)
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
    placeholder="Jaise: ek handsome Indian boy cafe mein baitha hai, soft cinematic evening lighting, candid photo"
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

chosen_label = st.selectbox("Neural Voice Model Chunein:", list(voice_options.keys()))
selected_voice_key = voice_options[chosen_label]

# Strict Real Live-Action Booster
LIVE_ACTION_BOOST = (
    ", professional raw unedited DSLR photograph, shot on Sony A7R IV, 50mm lens, f/1.4 aperture, "
    "authentic human skin texture, natural pores, candid facial expressions, realistic ambient lighting, "
    "real-world environment, zero cgi, zero animation, zero zoom, static sharp photo, 8k resolution, photorealistic"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate HD Reel Video"):
    if not user_prompt.strip():
        st.warning("Kripya video ka prompt zaroor likhein.")
    elif not voice_text.strip():
        st.warning("Kripya voiceover script zaroor likhein.")
    else:
        # Structure prompt
        base_subject = ""
        if "Female" in gender_choice:
            base_subject = "A sharp candid portrait of a real Indian young woman, "
        elif "Male" in gender_choice:
            base_subject = "A sharp candid portrait of a real Indian young man, "
        else:
            base_subject = "A sharp realistic raw documentary photo of "
            
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
                    target_duration = min(temp_audio_clip.duration + 0.5, 30.0)
                    temp_audio_clip.close()
            except Exception as e:
                st.error(f"Voice generation error: {e}")
                st.stop()

        # Step 2: Generate HD Image with Auto-Retry Mechanism
        img_path = "temp_reel_frame.jpg"
        image_success = False
        
        with st.spinner("Step 2/3: High-definition image render ho rahi hai (Auto-retry active)..."):
            encoded_prompt = urllib.parse.quote(final_prompt)
            
            # Multiple backup API endpoints / seeds for 100% reliability
            api_urls = [
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux-realism&nologo=true",
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux&nologo=true",
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&nologo=true"
            ]
            
            for attempt, img_url in enumerate(api_urls):
                try:
                    response = requests.get(img_url, timeout=45)
                    if response.status_code == 200 and len(response.content) > 1500:
                        with open(img_path, "wb") as f:
                            f.write(response.content)
                        image_success = True
                        break
                except Exception:
                    time.sleep(2) # Wait 2 seconds before trying next backup URL
                    continue
            
            if not image_success:
                st.error("Server par traffic zyada hone ki wajah se image load nahi ho paayi. Kripya 10 segundos baad 'Generate HD Reel Video' par dobara click karein.")
                st.stop()
            
            # Convert to Video (Static HD Image)
            try:
                temp_video = "temp_raw_reel_video.mp4"
                try:
                    img_clip = ImageClip(img_path, duration=target_duration)
                except TypeError:
                    img_clip = ImageClip(img_path).set_duration(target_duration)

                img_clip.write_videofile(
                    temp_video, 
                    fps=24, 
                    codec="libx264", 
                    audio=False,
                    preset="medium"
                )
                img_clip.close()
            except Exception as e:
                st.error(f"Video rendering error: {e}")
                st.stop()

        # Step 3: Merge Audio & Static Video Perfectly
        with st.spinner("Step 3/3: Voiceover aur HD image ko sync karke final reel ban rahi hai..."):
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
                
                st.success("Aapki Instagram HD Reel taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download HD Reel (MP4)",
                        data=file,
                        file_name="my_hd_reel.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Merging error: {e}")
