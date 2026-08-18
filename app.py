import os
import tempfile
import textwrap

import numpy as np
import soundfile as sf
import streamlit as st
from gradio_client import Client, handle_file
from huggingface_hub import InferenceClient
from kokoro import KPipeline
from moviepy.editor import AudioFileClip, ColorClip, CompositeVideoClip, TextClip

MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
HF_TOKEN = st.secrets.get("HF_TOKEN", os.environ.get("HF_TOKEN"))
# External HF Space for the talking-avatar feature. Defaults to kevinwang676/SadTalker,
# verified live and running on 2026-08-19. Override via the SADTALKER_SPACE secret if it
# ever goes down — third-party Spaces aren't guaranteed to stay up. See README.
SADTALKER_SPACE = st.secrets.get("SADTALKER_SPACE", os.environ.get("SADTALKER_SPACE", "kevinwang676/SadTalker"))

client = InferenceClient(model=MODEL, token=HF_TOKEN)


@st.cache_resource
def get_tts_pipeline():
    return KPipeline(lang_code="a")  # American English


def generate_text(resume_text, job_description):
    bullets_prompt = (
        "You are a resume writing assistant. Given the resume and job description below, "
        "rewrite the 5 most relevant resume bullet points to better match the job, using strong "
        "action verbs and quantifiable results where possible. Do not invent facts not present in "
        "the resume.\n\nRESUME:\n" + resume_text + "\n\nJOB DESCRIPTION:\n" + job_description +
        "\n\nReturn only the 5 bullet points, one per line."
    )
    cover_letter_prompt = (
        "You are a cover letter writing assistant. Given the resume and job description below, "
        "write a concise, spoken-style cover letter tailored to the role, 120-150 words so it "
        "reads aloud in about 45 seconds. Do not invent facts not present in the resume.\n\n"
        "RESUME:\n" + resume_text + "\n\nJOB DESCRIPTION:\n" + job_description
    )

    bullets = client.text_generation(bullets_prompt, max_new_tokens=300)
    cover_letter = client.text_generation(cover_letter_prompt, max_new_tokens=220)
    return bullets, cover_letter


def synthesize_audio(cover_letter_text):
    tts_pipeline = get_tts_pipeline()
    audio_chunks = [audio for _, _, audio in tts_pipeline(cover_letter_text, voice="af_heart")]
    audio = np.concatenate(audio_chunks)
    audio_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    sf.write(audio_path, audio, 24000)
    return audio_path


def render_visual_video(cover_letter_text, audio_path):
    """Guaranteed-to-work path: captioned background + voiceover. No GPU needed."""
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    background = ColorClip(size=(1280, 720), color=(15, 23, 42), duration=duration)
    caption = (
        TextClip(
            textwrap.fill(cover_letter_text, width=48),
            fontsize=32,
            color="white",
            size=(1100, 600),
            method="caption",
        )
        .set_duration(duration)
        .set_position("center")
    )

    video = CompositeVideoClip([background, caption]).set_audio(audio_clip)
    video_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    video.write_videofile(video_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    return video_path


def render_avatar_video(photo_path, audio_path):
    """Best-effort talking-avatar video via an external, already GPU-provisioned SadTalker
    Space, so this stays $0 for us. Returns None on any failure (not configured, Space down,
    API mismatch, timeout) so the caller can fall back to the guaranteed voiceover video.

    Signature verified live against kevinwang676/SadTalker's /info endpoint on 2026-08-19:
    it's an UNNAMED endpoint (fn_index=0, not api_name), 8 positional args in this order:
    source image, input audio, preprocess mode, still mode, GFPGAN enhancer, batch size,
    face resolution, pose style. Third-party Spaces can go down or change their signature
    without notice — reverify before pointing real users at this.
    """
    if not SADTALKER_SPACE or not photo_path:
        return None
    try:
        avatar_client = Client(SADTALKER_SPACE)
        result = avatar_client.predict(
            handle_file(photo_path),  # Source image
            handle_file(audio_path),  # Input audio
            "crop",  # preprocess
            True,  # Still Mode (fewer head movements — better fit for a professional video)
            True,  # GFPGAN as Face enhancer
            1,  # batch size in generation
            "256",  # face model resolution
            0,  # Pose style
            fn_index=0,
        )
        return result
    except Exception:
        return None


st.set_page_config(page_title="Resume & Cover Letter Tailor")
st.title("Resume & Cover Letter Tailor")
st.write(
    "Paste your resume and a job description. Get tailored bullet points, a draft cover "
    "letter, a 30-60 second voiceover video of it, and — optionally — a talking-avatar "
    "video using your own photo. All from open-source models."
)

resume_text = st.text_area("Your resume (paste text)", height=300)
job_description = st.text_area("Job description (paste text)", height=300)
photo = st.file_uploader(
    "Your photo (optional — for talking-avatar video, clear front-facing shot works best)",
    type=["png", "jpg", "jpeg"],
)

if st.button("Tailor it", type="primary"):
    if not resume_text.strip() or not job_description.strip():
        st.warning("Paste both your resume text and the job description first.")
    else:
        with st.spinner("Generating tailored bullet points and cover letter..."):
            bullets, cover_letter = generate_text(resume_text, job_description)

        st.subheader("Tailored bullet points")
        st.text(bullets)
        st.subheader("Draft cover letter")
        st.text(cover_letter)

        with st.spinner("Generating voiceover video (can take a minute or more)..."):
            audio_path = synthesize_audio(cover_letter)
            visual_video_path = render_visual_video(cover_letter, audio_path)
        st.subheader("Voiceover video")
        st.video(visual_video_path)

        if photo is not None:
            photo_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            with open(photo_path, "wb") as f:
                f.write(photo.getbuffer())
            with st.spinner("Generating talking-avatar video (best-effort, can take a few minutes)..."):
                avatar_video_path = render_avatar_video(photo_path, audio_path)
            if avatar_video_path:
                st.subheader("Talking-avatar video")
                st.video(avatar_video_path)
            else:
                st.info(
                    "Talking-avatar video wasn't available this time (the external service "
                    "may be busy or down) — showing the voiceover video only."
                )

st.markdown("---")
st.markdown(
    "Found this useful? [Buy me a coffee](https://buymeacoffee.com/YOUR_USERNAME) — "
    "helps keep it free."
)
