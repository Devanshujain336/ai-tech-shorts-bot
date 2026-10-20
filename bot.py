import os
import time
import json
import wave
import random
import asyncio
import datetime
import subprocess
import urllib.parse
import requests
import feedparser
import numpy as np
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from groq import Groq
import edge_tts
from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# 0. VERIFY YOUTUBE LOGIN
# ==========================================
def get_youtube_client():
    print("🔐 Step 0: Verifying YouTube Cloud Login...")
    client_id = "".join(os.environ.get("YT_CLIENT_ID", "").split())
    client_secret = "".join(os.environ.get("YT_CLIENT_SECRET", "").split())
    refresh_token = "".join(os.environ.get("YT_REFRESH_TOKEN", "").split())

    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)

# ==========================================
# 1. CONFIGURATION & SCHEMA
# ==========================================
GEMINI_API_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
PIXABAY_API_KEY = "".join(os.environ.get("PIXABAY_API_KEY", "").split())
VOICE = "en-US-ChristopherNeural"

class CinematicShort(BaseModel):
    title: str = Field(description="Viral YouTube Short title under 55 chars, must end with #ai #tech #shorts")
    description: str = Field(description="2-sentence summary of the AI news + 10 viral tech hashtags")
    tags: list[str] = Field(description="8 high-volume search tags")
    hook_badge: str = Field(description="3-4 word shocking headline banner for the first 3 seconds")
    sentences: list[str] = Field(description="Exactly 5 extremely short, punchy sentences (MAX 75 WORDS TOTAL).")
    ai_image_prompts: list[str] = Field(description="Exactly 5 detailed image prompts for 9:16 cinematic art. NO TEXT.")
    pixabay_fallbacks: list[str] = Field(description="Exactly 5 simple 1-2 word Pixabay search terms.")

# ==========================================
# 2. MULTI-PROVIDER LLM ROUTER (GEMINI + GROQ)
# ==========================================
def generate_ai_tech_plan():
    print("📡 Step 1: Scraping AI News (Multi-Provider Engine)...")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    if now_utc.hour < 7:
        search_query, sub_niche = "OpenAI+OR+ChatGPT+OR+Google+Gemini+when:1d", "AI Models & Giants"
    elif now_utc.hour < 12:
        search_query, sub_niche = "Humanoid+Robot+OR+Nvidia+OR+Elon+Musk+AI+when:1d", "Robotics & Hardware"
    else:
        search_query, sub_niche = "Artificial+Intelligence+Breakthrough+OR+Cybersecurity+when:1d", "Dark Tech & Breakthroughs"

    rss_url = f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    headlines = [entry.title for entry in feed.entries[:15]]
    
    prompt = f"""
    You are writing a script for a viral, documentary-style Tech YouTube Short (Niche: {sub_niche}).
    Headlines from today: {headlines}
    
    Pick the craziest story. Write a 5-sentence script.
    CRITICAL: Total script must be under 75 words for Shorts duration.
    Provide 5 incredibly detailed prompts for an AI Image Generator for each sentence.
    """

    # Try Gemini First
    if GEMINI_API_KEY:
        client_gemini = genai.Client(api_key=GEMINI_API_KEY)
        for model in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
            try:
                print(f"   🤖 Trying Gemini ({model})...")
                response = client_gemini.models.generate_content(
                    model=model, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=CinematicShort, temperature=0.75)
                )
                if response and response.text:
                    return json.loads(response.text)
            except Exception as e:
                print(f"   ⚠️ Gemini {model} busy. Trying next...")

    # Fallback to Groq
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    if GROQ_API_KEY:
        print("   🔄 Failing over to Groq (Llama 3.3)...")
        client_groq = Groq(api_key=GROQ_API_KEY)
        system_prompt = "You are a JSON-only API. Output valid JSON matching the CinematicShort schema."
        try:
            completion = client_groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"   ❌ Groq failed: {e}")

    raise RuntimeError("❌ Both LLM providers failed.")

# ==========================================
# 3. VOICE & CINEMATIC SOUND DESIGN
# ==========================================
async def generate_voiceover_and_timings(sentences):
    print("🎙️ Step 2: Generating fast documentary voiceover...")
    audio_files, durations = [], []
    for i, sentence in enumerate(sentences):
        filename = f"voice_{i}.mp3"
        communicate = edge_tts.Communicate(sentence, VOICE, rate="+25%", pitch="-2Hz") 
        await communicate.save(filename)
        clip = AudioFileClip(filename)
        durations.append(clip.duration)
        clip.close()
        audio_files.append(filename)
    print(f"⏱️ TOTAL DURATION: {sum(durations):.2f}s")
    return audio_files, durations

def generate_cinematic_audio(total_duration, cut_times):
    sr = 44100
    t = np.linspace(0, total_duration, int(sr * total_duration), endpoint=False)
    bgm = 0.05 * np.sin(2 * np.pi * 45 * t) + 0.02 * np.sin(2 * np.pi * 90 * t)
    
    # Cinematic Boom SFX
    boom_len = int(2.5 * sr)
    if boom_len < len(bgm):
        boom_t = np.linspace(0, 1, boom_len)
        bgm[:boom_len] += 0.6 * np.sin(2 * np.pi * (150 * np.exp(-5 * boom_t)) * boom_t) * np.exp(-3 * boom_t)

    # Cut whooshes
    for ct in cut_times:
        idx = int(ct * sr)
        if idx + int(0.3*sr) < len(bgm):
            bgm[idx:idx+int(0.3*sr)] += np.random.normal(0, 0.1, int(0.3*sr))
            
    pcm = (np.clip(bgm, -0.9, 0.9) * 32767).astype(np.int16)
    with wave.open("cinematic_sfx.wav", "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(pcm.tobytes())
        
    layers = [AudioFileClip("cinematic_sfx.wav")]
    if os.path.exists("bg_music.mp3") and os.path.getsize("bg_music.mp3") > 10000:
        try:
            custom_bg = AudioFileClip("bg_music.mp3").subclip(0, total_duration).volumex(0.15)
            layers.append(custom_bg)
        except: pass
    return CompositeAudioClip(layers)

# ==========================================
# 4. VISUAL ENGINE (VEO-STYLE KEN BURNS)
# ==========================================
def fetch_visual(ai_prompt, pix_query, duration, idx):
    img_path = f"img_{idx}.jpg"
    out_video = f"scene_{idx}.mp4"
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(ai_prompt)}?width=1080&height=1920&nologo=true&seed={random.randint(1,999)}"
    
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            with open(img_path, "wb") as f: f.write(r.content)
            frames = int(duration * 30)
            cmd = ["ffmpeg", "-y", "-loop", "1", "-i", img_path, "-t", f"{duration:.3f}", "-vf", f"scale=1080:1920,zoompan=z='min(zoom+0.0008,1.15)':d={frames}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,vignette=PI/3,fps=30", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", out_video]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return out_video
    except: pass

    # Pixabay Fallback
    try:
        r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(pix_query)}&orientation=vertical").json()
        video_url = r["hits"][0]["videos"]["medium"]["url"]
        with open(f"raw_{idx}.mp4", "wb") as f: f.write(requests.get(video_url).content)
        subprocess.run(["ffmpeg", "-y", "-i", f"raw_{idx}.mp4", "-t", f"{duration:.3f}", "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30", "-an", out_video], stdout=subprocess.DEVNULL)
        return out_video
    except:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration:.3f}", out_video], stdout=subprocess.DEVNULL)
        return out_video

# ==========================================
# 5. CAPTIONS & RENDERING
# ==========================================
def create_captions(sentences, durations, hook_badge):
    header = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Pop,Arial,90,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,8,5,2,60,60,550,1\nStyle: Hook,Arial,55,&H000000FF,&H000000FF,&H00FFFFFF,&HC0000000,-1,0,0,0,100,100,2,0,3,15,0,8,50,50,220,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events = [f"Dialogue: 1,0:00:00.00,0:00:03.50,Hook,,0,0,0,,🚨 {hook_badge.upper()} 🚨"]
    t = 0.0
    for s, d in zip(sentences, durations):
        words = s.upper().split()
        chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
        for chunk in chunks:
            dt = d / len(chunks)
            start = f"{int(t//3600)}:{int((t%3600)//60):02d}:{int(t%60):02d}.{int((t%1)*100):02d}"
            t += dt
            end = f"{int(t//3600)}:{int((t%3600)//60):02d}:{int(t%60):02d}.{int((t%1)*100):02d}"
            events.append(f"Dialogue: 0,{start},{end},Pop,,0,0,0,,{{\\fscx130\\fscy130\\t(0,100,\\fscx100\\fscy100)}}{chunk}")
    with open("caps.ass", "w") as f: f.write(header + "\n".join(events))
    return "caps.ass"

def render_and_upload(clips, audio_files, durations, plan, ass_file):
    print("🔥 Step 5: Rendering & Uploading...")
    with open("list.txt", "w") as f:
        for c in clips: f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "v.mp4"], check=True)
    
    full_voice = concatenate_audioclips([AudioFileClip(a) for a in audio_files])
    sfx = generate_cinematic_audio(full_voice.duration, np.cumsum(durations)[:-1])
    CompositeAudioClip([full_voice, sfx]).write_audiofile("a.m4a", fps=44100, codec="aac")
    
    subprocess.run(["ffmpeg", "-y", "-i", "v.mp4", "-i", "a.m4a", "-vf", f"ass={ass_file}", "-c:v", "libx264", "-b:v", "8000k", "-shortest", "final.mp4"], check=True)

    yt = get_youtube_client()
    now = datetime.datetime.now(datetime.timezone.utc)
    pub = (now + datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {"snippet": {"title": plan["title"][:90], "description": plan["description"], "categoryId": "28"}, "status": {"privacyStatus": "private", "publishAt": pub}}
    yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload("final.mp4", mimetype="video/mp4")).execute()
    print(f"🎉 Scheduled for {pub}")

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    plan = generate_ai_tech_plan()
    audio_files, durations = asyncio.run(generate_voiceover_and_timings(plan["sentences"]))
    clips = [fetch_visual(p, f, d, i) for i, (p, f, d) in enumerate(zip(plan["ai_image_prompts"], plan["pixabay_fallbacks"], durations))]
    ass_file = create_captions(plan["sentences"], durations, plan["hook_badge"])
    render_and_upload(clips, audio_files, durations, plan, ass_file)
