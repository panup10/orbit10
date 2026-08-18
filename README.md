# Resume & Cover Letter Tailor

Free web app: paste a resume + job description, get tailored bullet points, a draft
cover letter, a 30-60 second voiceover video of it, and — optionally — a talking-avatar
version using the applicant's own uploaded photo. All from open-source models.

Two video outputs:
- **Voiceover video** (always generated): TTS voiceover (Kokoro, open-source) over a
  captioned background, rendered to MP4 with ffmpeg/moviepy. Runs entirely on our own
  free host. This is the guaranteed one.
- **Talking-avatar video** (best-effort, only if a photo is uploaded): the uploaded photo
  lip-synced to the same voiceover audio, via an external SadTalker-compatible Hugging
  Face Space (`kevinwang676/SadTalker`, verified live 2026-08-19) called through
  `gradio_client`. This offloads the GPU-heavy part to a Space that already has GPU,
  keeping our own cost at $0 — but it's a dependency on someone else's Space staying up,
  so it's designed to fail silently and fall back to just the voiceover video.

## Hosting: Streamlit Community Cloud, not Hugging Face Spaces

We originally planned to host this on Hugging Face Spaces (free Gradio CPU tier). As of
2026-08-19, HF now requires a paid PRO plan to create a Gradio or Docker Space — only
static (no-backend) Spaces are free, which this app can't run on since it needs a Python
backend. Confirmed live in your own HF account: both Gradio and Docker showed "Paid"
locks at Space creation.

Streamlit Community Cloud was checked and is confirmed free ("Totally free" per their own
pricing page) for public apps, with no paid tier for basic hosting. The app was rewritten
from Gradio to Streamlit for this — the actual generation logic (LLM calls, TTS, video
rendering) didn't change, only the UI layer.

Tradeoff to know about: Streamlit Community Cloud's free tier is **public apps deployed
from a public GitHub repo** — meaning your source code (this folder) needs to live in a
public GitHub repository. No credentials are ever in the code (they go in Streamlit's own
Secrets manager, see below), so nothing sensitive gets exposed by this.

## Deploy (free, ~15 min, needs a human)

1. Create a free GitHub account at https://github.com, if you don't have one.
2. Create a new **public** repository and push the contents of this folder to it
   (`app.py`, `requirements.txt`, `packages.txt`, `README.md`).
3. Create a free account at https://streamlit.io/cloud (sign in with GitHub is easiest).
4. Click "New app", pick your repository/branch, and set **Main file path** to `app.py`.
5. Before or after first deploy, open the app's **Settings → Secrets** in Streamlit Cloud
   and add (TOML format):
   ```
   HF_TOKEN = "your-hugging-face-token-here"
   ```
   Get the token from https://huggingface.co/settings/tokens (read access is enough).
   Never commit this value into the GitHub repo itself.
6. Click Deploy. Streamlit Cloud installs `requirements.txt` (Python packages) and
   `packages.txt` (system packages: `ffmpeg`, `espeak-ng`) automatically.
7. Once live, edit `app.py` (in GitHub) to replace `YOUR_USERNAME` in the Buy Me a Coffee
   link with your own (create a free account at https://buymeacoffee.com first) — push
   the change and Streamlit Cloud auto-redeploys.

Talking-avatar video needs no extra setup — `kevinwang676/SadTalker` is wired in as the
default. Only add a `SADTALKER_SPACE` secret if that Space ever goes down and you switch
to another one.

## Known risks (flagging per prompt's UNCERTAINTY rule)

- This is a genuinely new hosting target for this project — nothing about it has been
  deployed and run for real yet. First deploy is also the first real end-to-end test.
- Free compute (Streamlit Cloud's CPU tier) may be slow for TTS + video rendering; a
  single request could take well over a minute.
- Exact package availability/versions for `kokoro` on Streamlit Cloud's build haven't
  been test-installed — first deploy may surface a dependency fix needed.
- The talking-avatar path depends on kevinwang676/SadTalker staying up and unchanged —
  confirmed live and its API signature confirmed on 2026-08-19, but third-party Spaces
  can go down or change without notice after that.
- Streamlit Community Cloud's free tier requires the source repo to be public — confirm
  you're fine with that before pushing (no secrets are in the code, but the code and its
  logic are visible to anyone).
- Uploading a real photo for lip-sync is a legitimate video-resume use case, but the
  SadTalker Space's own data-retention practices for uploaded photos haven't been
  confirmed — check its terms before pointing real users at it.

## Status

MVP v0.4 (Streamlit rewrite, HF Spaces path abandoned due to pricing change) — not yet
deployed. First $ target: first tip received after deploy + first share.
