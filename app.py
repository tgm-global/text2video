
import streamlit as st
import os
import cv2
import numpy as np
import asyncio
import edge_tts
import subprocess
import tempfile
import textwrap
import math

from PIL import Image, ImageDraw, ImageFont

st.set_page_config(
    page_title="AI Reels Studio",
    page_icon="🎬",
    layout="centered"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#101426,#191d35);
    color: white;
}
h1 {
    text-align: center;
    color: #ffffff;
}
.stButton button {
    background: #7c3aed;
    color: white;
    border-radius: 12px;
    width: 100%;
    height: 50px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.title("🎬 AI REELS STUDIO")
st.caption("Create cinematic Instagram Reels from your story")

st.divider()

story = st.text_area(
    "✍️ Apni story likhein",
    height=180,
    placeholder="Ek gareeb ladke ki kahani..."
)

st.subheader("🎞️ Upload Cinematic Scenes")

images = st.file_uploader(
    "Scene images upload karein",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

voice = st.selectbox(
    "🎙️ Hindi AI Voice",
    [
        "hi-IN-SwaraNeural",
        "hi-IN-MadhurNeural"
    ]
)

quality = st.selectbox(
    "Video Quality",
    ["720p HD", "1080p Full HD"]
)

duration_limit = st.slider(
    "Maximum Reel Duration (seconds)",
    15, 60, 30
)

music = st.file_uploader(
    "🎵 Background Music (Optional)",
    type=["mp3", "wav"]
)


def split_story(text):
    text = text.replace("\r", "")
    paragraphs = [
        p.strip() for p in text.split("\n")
        if p.strip()
    ]

    if len(paragraphs) > 1:
        return paragraphs

    sentences = []
    for part in text.replace("!", "।").replace("?", "।").split("।"):
        if part.strip():
            sentences.append(part.strip())

    return sentences


def get_font(size):
    fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]

    for path in fonts:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass

    return ImageFont.load_default()


async def generate_voice(text, path, voice_name):
    tts = edge_tts.Communicate(
        text=text,
        voice=voice_name,
        rate="+0%",
        volume="+0%"
    )
    await tts.save(path)


def make_cinematic_frame(image, width, height, progress, caption):

    image = image.convert("RGB")

    ratio = max(
        width / image.width,
        height / image.height
    )

    nw = int(image.width * ratio)
    nh = int(image.height * ratio)

    image = image.resize((nw, nh))

    zoom = 1 + (0.12 * progress)

    crop_w = int(width / zoom)
    crop_h = int(height / zoom)

    max_x = max(0, nw - crop_w)
    max_y = max(0, nh - crop_h)

    x = int(max_x * progress)
    y = int(max_y * progress)

    image = image.crop((
        x, y, x + crop_w, y + crop_h
    ))

    image = image.resize((width, height))

    image = np.array(image).astype(np.float32)

    # Cinematic contrast
    image = (image - 110) * 1.12 + 110
    image = np.clip(image, 0, 255).astype(np.uint8)

    pil = Image.fromarray(image).convert("RGBA")

    overlay = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(overlay)

    draw.rectangle(
        (0, int(height * 0.72), width, height),
        fill=(0, 0, 0, 175)
    )

    pil = Image.alpha_composite(pil, overlay)

    draw = ImageDraw.Draw(pil)

    font = get_font(36 if width >= 1080 else 25)

    lines = textwrap.wrap(caption, width=30)

    y_text = int(height * 0.78)

    for line in lines[:4]:

        bbox = draw.textbbox(
            (0, 0), line, font=font
        )

        tw = bbox[2] - bbox[0]

        draw.text(
            ((width - tw) // 2, y_text),
            line,
            font=font,
            fill="white",
            stroke_width=2,
            stroke_fill="black"
        )

        y_text += 48 if width >= 1080 else 34

    return cv2.cvtColor(
        np.array(pil.convert("RGB")),
        cv2.COLOR_RGB2BGR
    )


def create_reel(
    images,
    scenes,
    audio,
    output,
    width,
    height,
    max_duration,
    music_path=None
):

    probe = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio
        ],
        capture_output=True,
        text=True,
        check=True
    )

    audio_duration = float(probe.stdout.strip())

    if audio_duration > max_duration:
        raise ValueError(
            "Voiceover duration exceeds selected maximum. "
            "Please shorten your story."
        )

    fps = 20
    scene_duration = audio_duration / len(scenes)

    silent = output.replace(".mp4", "_silent.mp4")

    writer = cv2.VideoWriter(
        silent,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height)
    )

    if not writer.isOpened():
        raise RuntimeError("Video writer could not start.")

    for i, caption in enumerate(scenes):

        count = max(
            1,
            int(scene_duration * fps)
        )

        image = images[i % len(images)]

        for frame_no in range(count):

            progress = frame_no / max(1, count - 1)

            frame = make_cinematic_frame(
                image,
                width,
                height,
                progress,
                caption
            )

            writer.write(frame)

    writer.release()

    command = [
        "ffmpeg",
        "-y",
        "-i", silent,
        "-i", audio
    ]

    if music_path:

        command += [
            "-stream_loop", "-1",
            "-i", music_path,
            "-filter_complex",
            "[2:a]volume=0.12[m];"
            "[1:a][m]amix=inputs=2:duration=first[a]",
            "-map", "0:v",
            "-map", "[a]"
        ]

    else:

        command += [
            "-map", "0:v",
            "-map", "1:a"
        ]

    command += [
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output
    ]

    try:
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
    finally:
        if os.path.exists(silent):
            os.remove(silent)


st.divider()

if st.button("🚀 GENERATE MY AI REEL"):

    if not story.strip():
        st.error("Please enter your story.")
        st.stop()

    if not images:
        st.error("Please upload scene images.")
        st.stop()

    if len(story) > 4000:
        st.error("Story should be under 4000 characters.")
        st.stop()

    scenes = split_story(story)

    if len(scenes) > 15:
        st.error("Maximum 15 scenes allowed.")
        st.stop()

    with tempfile.TemporaryDirectory() as temp:

        audio_path = os.path.join(temp, "voice.mp3")
        output_path = os.path.join(temp, "final_reel.mp4")

        try:

            progress = st.progress(0)
            status = st.empty()

            status.write("🎙️ Generating Hindi voiceover...")

            asyncio.run(
                generate_voice(
                    story,
                    audio_path,
                    voice
                )
            )

            progress.progress(25)

            status.write("🎬 Loading cinematic images...")

            scene_images = []

            for file in images:

                img = Image.open(file).convert("RGB")
                scene_images.append(img)

            width, height = (
                (720, 1280)
                if quality == "720p HD"
                else (1080, 1920)
            )

            music_path = None

            if music:

                music_path = os.path.join(
                    temp, "music.mp3"
                )

                with open(music_path, "wb") as f:
                    f.write(music.getvalue())

            progress.progress(40)

            status.write("🎥 Rendering cinematic video...")

            create_reel(
                scene_images,
                scenes,
                audio_path,
                output_path,
                width,
                height,
                duration_limit,
                music_path
            )

            progress.progress(100)

            status.success("🎉 Your Reel is ready!")

            with open(output_path, "rb") as f:
                video = f.read()

            st.video(video)

            st.download_button(
                "⬇️ DOWNLOAD YOUR REEL",
                data=video,
                file_name="AI_Reel.mp4",
                mime="video/mp4"
            )

        except Exception as e:

            st.error(
                f"Generation error: {str(e)}"
            )
