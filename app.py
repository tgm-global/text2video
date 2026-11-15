import streamlit as st
import requests
import os
import asyncio
import edge_tts
import urllib.parse
import time

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

st.set_page_config(page_title="Multi-Scene Story Reel Generator", layout="centered")
st.title("AI Story Reel Generator (Multi-Scene)")
st.write("Apni emotional story script daalein, tool khud alag-alag scenes aur voiceover wali HD Reel bana dega.")

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
    "Apni poori Story / Script yahan likhein (Hindi / Hinglish / English):",
    value="Ek ladka roz ek ladki ko park mein dekhta tha. Ladki jab bhi muskurati, ladke ka din ban jaata. Ek din himmat karke ladke ne ladki se baat ki. Dheere-dheere dono dost bane aur phir ek doosre se pyaar karne lage.\nDono saath ghoomte, coffee peete aur apne future ke sapne dekhte. Ek din ladki ko doosre shehar jaana pada. Jaate waqt usne ladke se kaha, 'Kya tum mera intezaar karoge?'\nLadke ne muskurakar kaha, 'Jab mohabbat sachchi ho, toh intezaar bhi khoobsurat lagta hai.'\nKuch mahino baad ladki wapas aayi. Ladka aaj bhi usi park mein uska intezaar kar raha تھا۔ Dono ek doosre ko dekhkar muskuraaye aur gale lag gaye.",
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

# Strict Real Live-Action Booster
LIVE_ACTION_BOOST = (
    ", professional raw unedited DSLR photograph, shot on Sony A7R IV, 50mm lens, f/1.4 aperture, "
    "authentic human skin texture, natural pores, candid facial expressions, realistic ambient lighting, "
    "real-world environment, zero cgi, zero animation, static sharp photo, 8k resolution, photorealistic"
)

async def generate_edge_tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if st.button("Generate Full Story Reel"):
    if not story_script.strip():
        st.warning("Kripya story script zaroor likhein.")
    else:
        # Step 1: Generate full voiceover audio first
        audio_path = "temp_full_story_audio.mp3"
        with st.spinner("Step 1/4: Emotional neural voiceover generate ho raha hai..."):
            try:
                asyncio.run(generate_edge_tts(story_script, selected_voice_key, audio_path))
                if not os.path.exists(audio_path):
                    st.error("Voice generation fail ho gaya.")
                    st.stop()
            except Exception as e:
                st.error(f"Voice error: {e}")
                st.stop()

        # Step 2: Split story into 4 distinct visual scenes based on the narrative flow
        scene_prompts = [
            f"A romantic young Indian man and woman smiling at each other in a lush green public park, golden hour sunlight, candid street photography {LIVE_ACTION_BOOST}",
            f"A romantic couple sitting together in a cozy modern cafe, drinking coffee, laughing happily, intimate candid shot {LIVE_ACTION_BOOST}",
            f"A heartbroken young man standing alone at a railway station platform looking thoughtful and waiting, moody evening lighting {LIVE_ACTION_BOOST}",
            f"A happy emotional reunion of a young Indian couple hugging each other tightly in a park, sunset background, cinematic {LIVE_ACTION_BOOST}"
        ]
        
        scene_image_paths = []
        
        with st.spinner("Step 2/4: Story ke liye 4 alag-alag HD scenes render ho rahe hain..."):
            for i, prompt in enumerate(scene_prompts):
                encoded_prompt = urllib.parse.quote(prompt)
                img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={vid_width}&height={vid_height}&model=flux-realism&nologo=true"
                
                img_path = f"temp_scene_{i+1}.jpg"
                success = False
                
                for _ in range(2): # Retry once if fails
                    try:
                        res = requests.get(img_url, timeout=40)
                        if res.status_code == 200 and len(res.content) > 1500:
                            with open(img_path, "wb") as f:
                                f.write(res.content)
                            scene_image_paths.append(img_path)
                            success = True
                            break
                    except Exception:
                        time.sleep(1)
                
                if not success:
                    # Fallback default image if a scene fails
                    fallback_url = f"https://image.pollinations.ai/prompt/romantic%20couple%20in%20park%20photorealistic?width={vid_width}&height={vid_height}&nologo=true"
                    try:
                        res = requests.get(fallback_url, timeout=30)
                        if res.status_code == 200:
                            with open(img_path, "wb") as f:
                                f.write(res.content)
                            scene_image_paths.append(img_path)
                    except Exception:
                        pass

        if len(scene_image_paths) == 0:
            st.error("Visuals generate nahi ho paaye. Dobara koshish karein.")
            st.stop()

        # Step 3: Calculate duration per scene and build clips
        with st.spinner("Step 3/4: Scenes aur Audio ko sequence mein set kiya ja raha hai..."):
            try:
                audio_clip = AudioFileClip(audio_path)
                total_duration = audio_clip.duration
                scene_duration = total_duration / len(scene_image_paths) # Divide audio equally among scenes
                
                clip_files = []
                for i, img_p in enumerate(scene_image_paths):
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
                
                # Concatenate all scenes together
                loaded_clips = [VideoFileClip(c) for c in clip_files]
                final_video = concatenate_videoclips(loaded_clips, method="compose")
                
            except Exception as e:
                st.error(f"Scene compilation error: {e}")
                st.stop()

        # Step 4: Attach Audio to Final Video
        with st.spinner("Step 4/4: Final Story Reel taiyar ho rahi hai..."):
            try:
                if hasattr(final_video, "with_audio"):
                    final_video_with_audio = final_video.with_audio(audio_clip)
                else:
                    final_video_with_audio = final_video.set_audio(audio_clip)
                
                final_output_file = "story_reel_output.mp4"
                final_video_with_audio.write_videofile(
                    final_output_file, 
                    codec="libx264", 
                    audio_codec="aac", 
                    fps=24,
                    preset="medium"
                )
                
                # Cleanup temp files
                audio_clip.close()
                final_video.close()
                for c in clip_files:
                    if os.path.exists(c): os.remove(c)
                for img_p in scene_image_paths:
                    if os.path.exists(img_p): os.remove(img_p)
                if os.path.exists(audio_path): os.remove(audio_path)
                
                st.success("Aapki Emotional Story Reel safalpurvak taiyar hai!")
                st.video(final_output_file)
                
                with open(final_output_file, "rb") as file:
                    st.download_button(
                        label="Download Story Reel (MP4)",
                        data=file,
                        file_name="love_story_reel.mp4",
                        mime="video/mp4"
                    )
                    
            except Exception as e:
                st.error(f"Final merge error: {e}")
