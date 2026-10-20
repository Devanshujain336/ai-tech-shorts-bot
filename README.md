# 🚀 Autonomous Multi-Modal AI Video Generation & Distribution Pipeline

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Google%20Gemini-3.8%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Filtergraphs%20%26%20libass-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-DSP%20Audio%20Synthesis-013243?style=for-the-badge&logo=numpy&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Serverless%20CI%2FCD-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![YouTube API](https://img.shields.io/badge/YouTube%20Data%20API-v3-FF0000?style=for-the-badge&logo=youtube&logoColor=white)

An end-to-end, **zero-marginal-cost ($0/month)** cloud-native media pipeline that autonomously ingests real-time breaking tech news, orchestrates LLMs with deterministic schema validation, synthesizes neural speech and procedural sound effects via Digital Signal Processing (DSP), renders 1080p 9:16 vertical videos with kinetic typography, and schedules peak-hour uploads to **YouTube Shorts** and **Instagram Reels** 3x daily.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    A[⏰ GitHub Actions Cron<br/>3x Daily UTC Triggers] --> B[📡 Stateless RSS Ingestion<br/>Time-Windowed Topic Routing]
    B --> C[🧠 Gemini 3.8 Flash<br/>+ Pydantic JSON Schema]
    C -->|Multi-Model 503 Failover| D[🎙️ Async Edge-TTS<br/>Sentence-Level Timings]
    C --> E[🎨 3-Tier Visual Engine]
    
    D --> F[🔊 NumPy DSP Synthesizer<br/>180Hz-30Hz Sub-Bass Drop + Whoosh SFX]
    
    E -->|Tier 1| E1[Flux Diffusion 9:16 AI Art]
    E -->|Tier 2 Fallback| E2[Pixabay HD Video REST API]
    E -->|Tier 3 Fallback| E3[FFmpeg Lavfi Canvas]
    
    E1 & E2 & E3 --> G[🎬 FFmpeg zoompan Filtergraph<br/>Virtual Camera + Vignette 1080x1920]
    D --> H[⚡ SubStation Alpha .ASS Engine<br/>2-Word Pop-Up Kinetic Typography]
    
    F & G & H --> I[🔥 FFmpeg libx264 Compositor<br/>1080p 30FPS @ 8000kbps]
    I --> J[🚀 Headless OAuth 2.0 Distribution<br/>YouTube Data API v3 & Meta Graph API]
```

---

## ✨ Key Engineering Highlights

### 1. Deterministic LLM Orchestration (`google-genai` + `Pydantic`)
* Enforces strict **Pydantic (`BaseModel`)** response schemas on **Gemini 3.8 Flash**, guaranteeing structured JSON outputs containing SEO metadata, hook badges, time-constrained scripts (`<75 words` for strict `<60s` YouTube Shorts compliance), and visual prompts.
* Features an **automated multi-model failover loop** that dynamically queries `client.models.list()` to recover from `503 UNAVAILABLE` traffic spikes.

### 2. Procedural DSP Audio Synthesis (`NumPy` + `wave`)
* Eliminates external audio dependencies and copyright risks by synthesizing a **44.1kHz 16-bit PCM soundtrack** directly in memory using `NumPy`:
  * **Pattern-Interrupt Sub-Bass Drop:** Exponential frequency sweep (`180Hz → 30Hz` over `2.5s`) with harmonic wave-clipping distortion at `t = 0.0s`.
  * **Ambient Drone:** Continuous `45Hz` and `90Hz` dual-oscillator dark background pulse.
  * **Frame-Synced Whoosh Transitions:** Calculates cumulative scene durations (`np.cumsum`) and injects sine-enveloped Gaussian noise sweeps at every visual cut.

### 3. Programmatic Video Compositing & Kinetic Typography (`FFmpeg` + `libass`)
* **Virtual Camera Kinematics:** Applies FFmpeg `zoompan` filtergraphs (`s=1080x1920`, `fps=30`) with radial `vignette` shading to transform static diffusion generations into dynamic documentary scenes.
* **Vector Pop-Up Subtitles (`.ass`):** Generates character-weighted timestamps for 2-word chunks and injects SubStation Alpha override tags (`\fscx135\fscy135\t(0,100,\fscx100\fscy100)`) for 135%-to-100% bounce scaling and dynamic BGR hex color highlighting.

### 4. 3-Tier Self-Healing Visual Failover
* **Tier 1:** Requests custom 1080x1920 vertical AI visuals via Flux Diffusion with browser `User-Agent` spoofing and byte-length verification (`>30KB`).
* **Tier 2:** Automatically falls back to the **Pixabay Video REST API** if datacenter IPs are rate-limited.
* **Tier 3:** Generates a procedural `lavfi` canvas to guarantee zero pipeline crashes.

### 5. Stateless Topic Deduplication & Headless OAuth 2.0
* Prevents duplicate news coverage across stateless CI/CD runs via **UTC Time-Slotted Sub-Niche Routing** (*Morning: LLMs & Tech Giants | Afternoon: Robotics & Silicon | Evening: Cybersecurity & Breakthroughs*).
* Authenticates in headless Linux containers via sanitized **OAuth 2.0 Refresh Token rotation** and schedules uploads for peak viewership windows (`12:00 PM`, `05:30 PM`, and `09:00 PM IST`).

---

## 💰 Unit Economics (SaaS Cost Comparison)

| Component | Traditional Creator Stack | This Pipeline | Monthly Cost |
| :--- | :--- | :--- | :--- |
| **LLM Scripting** | OpenAI API / ChatGPT Plus | Gemini 3.8 Flash (Free Tier) | **$0.00** |
| **Voiceover (TTS)** | ElevenLabs ($22/mo) | Microsoft `edge-tts` Neural | **$0.00** |
| **Visuals & B-Roll** | Midjourney ($30/mo) | Flux API + Pixabay Fallback | **$0.00** |
| **Video Rendering** | Creatomate / Shotstack ($49/mo) | Custom `FFmpeg` + `.ass` Engine | **$0.00** |
| **Cloud Compute** | AWS EC2 / Zapier ($20/mo) | GitHub Actions Cron CI/CD | **$0.00** |
| **Total Monthly COGS** | **~$121.00 / month** | **100% Open-Source / Free Tier** | **$0.00 / mo** |

---

## ⚙️ Repository Structure & Deployment

```text
├── .github/
│   └── workflows/
│       └── daily_short.yml   # Serverless CI/CD cron workflow (3x daily)
├── bot.py                    # Core multi-modal generation & upload engine
└── README.md                 # System documentation
```

### Required GitHub Actions Secrets
Configure under **Settings → Secrets and variables → Actions → Repository secrets**:
* `GEMINI_API_KEY` – Google AI Studio API Key
* `PIXABAY_API_KEY` – Pixabay REST API Key
* `YT_CLIENT_ID` – Google Cloud OAuth 2.0 Client ID
* `YT_CLIENT_SECRET` – Google Cloud OAuth 2.0 Client Secret
* `YT_REFRESH_TOKEN` – Permanent Headless OAuth 2.0 Refresh Token
