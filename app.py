import streamlit as st
import requests
import os
import asyncio
import edge_tts
import urllib.parse
import time
import re

# Safe MoviePy Import (v1 & v2 compatible)
try:
    from moviepy import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips
except ImportError:
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips
    except ImportError:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.video.io.ImageClip import ImageClip
        from moviepy.video.compositing.concatenate import concatenate_videoclips

st.set_page_config(page_title="Animated Story Reel Generator (Word-by-Word Scene Changer)", layout="centered")
st.title("Animated Story Reel Generator")
st.write("Story daalein, aur tool har sentence ke sath automatic expressions aur scenes wali animated images change karte hue reel banayega.")

# 1. Format Selection (Reels 9:16)
aspect_ratio = st.selectbox(
    "Video Format Chunein:",
    ["9:16 (Instagram Reels / YouTube Shorts)", "16:9 (Landscape / Website)"]
)

if "9:16" in aspect_ratio:
    vid_width, vid_height = 576, 1024
else:
    vid_width, vid_height = 1024, 576

# 2. Story / Script Input
story_script = st.text_area(
    "Apni poori Story / Script yahan likhein:",
    value="Ek ladka roz ek ladki ko park mein dekhta tha. Ladki jab bhi muskurati, ladke ka din ban jaata. Ek din himmat karke ladke ne ladki se baat ki. Dheere-dheere dono dost bane aur phir ek doosre se pyaar karne lage. Dono saath ghoomte, coffee peete aur apne future ke sapne dekhte. Ek din ladki ko doosre shehar jaana pada. Jaate waqt usne ladke se kaha, 'Kya tum mera intezaar karoge?' Ladke ne muskurakar kaha, 'Jab mohabbat sachchi ho, toh intezaar bhi khoobsurat lagta hai.' Kuch mahino baad ladki wapas aayi. Ladka aaj bhi usi park mein uska intezaar kar raha tha. Dono ek doosre ko dekhkar muskuraaye aur gale lag gaye.",
    height=150
)

# 3. Voice Model Selection
voice_options = {
    "hi-IN-MadhurNeural (Hindi Male - Deep & Emotional)": "hi-IN-MadhurNeural",
    "hi-IN-SwaraNeural (Hindi Female - Warm & Expressive)": "hi-IN-SwaraNeural",
    "en-IN-PrabhatNeural (Indian Male - Clear)": "en-IN-PrabhatNeural",
    "en-IN-NeerjaNeural (Indian Female - Clear)": "en-IN-NeerjaNeural"
}

chosen_label = st.selectbox("Voiceover ke liye Narrator Chunein:", list(voice_options.keys()))
selected_voice_key = voice_options[chosen_label]

# Cartoon / 2D Animated Illustration Style Booster
CARTOON_ANIMATION_BOOST = (
    ", vibrant 2D animated vector art style, cute modern cartoon illustration, "
    "expressive character facial expressions, colorful and emotional storytelling aesthetic, "
    "clean lines, high quality digital artwork, storybook illustration"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate Dynamic Animated Reel"):
    if not story_script.strip():
        st.warning("Kripya story script zaroor likhein.")
    else:
        # Step 1: Split story into sentences using punctuation marks (. ! ?)
        sentences = [s.strip() for s in re.split(r'[.!?]+', story_script) if s.strip()]
        if not sentences:
            sentences = [story_script]
            
        st.info(f"Aapki story ko {len(sentences)} alag-alag animated scenes mein divide kiya gaya hai.")

        # Step 2: Generate full voiceover audio first to get exact duration
        audio_path = "temp_full_story_audio.mp3"
        with st.spinner("Step 1/3: Neural voiceover generate ho raha hai..."):
            try:
                asyncio.run(generate_edge_tts(story_script, selected_voice_key, audio_path))
                if not os.path.exists(audio_path):
                    st.error("Voice generation fail ho gaya.")
                    st.stop()
                
                audio_clip = AudioFileClip(audio_path)
                total_duration = audio_clip.duration
            except Exception as e:
                st.error(f"Voice error: {e}")
                st.stop()

        # Step 3: Generate matching animated image for each sentence sequentially
        scene_image_paths = []
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        total_sentences = len(sentences)
        
        for i, sentence in enumerate(sentences):
            progress_text.text(f"Step 2/3: Scene {i+1} of {total_sentences} ki animated image ban rahi hai...")
            progress_bar.progress(int(((i + 1) / total_sentences) * 100))
            
            # Combine sentence text with cartoon animation booster
            prompt_text = f"An illustrated scene showing: {sentence} {CARTOON_ANIMATION_BOOST}"
            encoded_prompt = urllib.parse.quote(prompt_text)
            img_path = f"temp_scene_{i}.jpg"
            success = False
            
            # Try endpoints with safe fallbacks
            urls = [
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux&nologo=true&seed={300+i}",
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&nologo=true&seed={400+i}"
            ]
            
            for url in urls:
                try:
                    res = requests.get(url, timeout=35)
                    if res.status_code == 200 and len(res.content) > 1500:
                        with open(img_path, "wb") as f:
                            f.write(res.content)
                        scene_image_paths.append(img_path)
                        success = True
                        break
                except Exception:
                    time.sleep(1)
                    continue
            
            if not success:
                # Fallback cartoon placeholder if a sentence image fails
                try:
                    fallback_url = f"https://image.pollinations.ai/prompt/cute%20cartoon%20romantic%20story%20illustration?width={vid_width}&height={vid_height}&nologo=true&seed={500+i}"
                    res = requests.get(fallback_url, timeout=20)
                    if res.status_code == 200:
                        with open(img_path, "wb") as f:
                            f.write(res.content)
                        scene_image_paths.append(img_path)
                except Exception:
                    pass
            
            time.sleep(1) # Delay to keep server stable

        progress_text.empty()
        progress_bar.empty()

        if len(scene_image_paths) == 0:
            st.error("Animated visuals generate nahi ho paaye. Dobara koshish karein.")
            st.stop()

        # Step 4: Calculate exact duration per sentence/scene and build video clips
        with st.spinner("Step 3/3: Har sentence ke hisaab se scenes aur audio ko sync kiya ja raha hai..."):
            try:
                # Distribute audio duration proportionally based on character length of each sentence
                total_chars = sum(len(s) for s in sentences)
                clip_files = []
                
                for i, img_p in enumerate(scene_image_paths):
                    # Proportional duration allocation per sentence
                    sentence_weight = len(sentences[i]) / max(total_chars, 1)
                    scene_duration = max(total_duration * sentence_weight, 2.0) # Minimum 2 seconds per scene
                    
                    out_clip_name = f"temp_clip_{i}.mp4"
                    try:
                        img_clip = ImageClip(img_p, duration=scene_duration)
                    except TypeError:
                        img_clip = ImageClip(img_p).set_duration(scene_duration)
                        
                    img_clip.write_videofile(
                        out_clip_name, 
                        fps=24, 
                        codec="libx264", 
                        audio=False,
                        preset="ultrafast"
                    )
                    img_clip.close()
                    clip_files.append(out_clip_name)
                
                loaded_clips = [VideoFileClip(c) for c in clip_files]
                final_video = concatenate_videoclips(loaded_clips, method="compose")
                
                # Attach audio
                if hasattr(final_video, "with_audio"):
                    final_video_with_audio = final_video.with_audio(audio_clip)
                else:
                    final_video_with_audio = final_video.set_audio(audio_clip)
                
                final_output_file = "animated_story_reel.mp4"
                final_video_with_audio.write_videofile(
                    final_output_file, 
                    codec="libx264", 
                    audio_codec="aac", 
                    fps=24,
                    preset="medium"
                )
                
                # Cleanup temporary files
                audio_clip.close()
                final_video.close()
                for c in clip_files:
                    if os.path.exists(c): os.remove(c)
                for img_p in scene_image_paths:
                    if os.path.exists(img_p): os.remove(img_p)
                if os.path.exists(audio_path): os.remove(audio_path)
                
                st.success("Aapki Dynamic Animated Story Reel taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Animated Reel (MP4)",
                        data=file,
                        file_name="animated_story_reel.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Video compilation error: {e}")
