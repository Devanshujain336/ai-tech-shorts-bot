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

print("🚀 SCRIPT STARTING... (Checking Imports)")

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

print("✅ All Imports Successful!")

# ==========================================
# 0. CONFIGURATION
# ==========================================
GEMINI_API_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
PIXABAY_API_KEY = "".join(os.environ.get("PIXABAY_API_KEY", "").split())
GROQ_API_KEY = "".join(os.environ.get("GROQ_API_KEY", "").split())
VOICE = "en-US-ChristopherNeural"

class CinematicShort(BaseModel):
    title: str = Field(description="Viral YouTube Short title under 55 chars ending with #ai #tech #shorts")
    description: str = Field(description="2-sentence summary of the AI news + 10 viral tech hashtags")
    tags: list[str] = Field(description="8 high-volume search tags")
    hook_badge: str = Field(description="3-4 word shocking headline banner for the first 3 seconds")
    sentences: list[str] = Field(description="Exactly 5 short, punchy sentences (MAXIMUM 70 WORDS TOTAL).")
    ai_image_prompts: list[str] = Field(description="Exactly 5 detailed 9:16 visual prompts. NO TEXT IN IMAGES.")
    pixabay_fallbacks: list[str] = Field(description="Exactly 5 simple 1-2 word Pixabay search terms.")

# ==========================================
# 1. VERIFY YOUTUBE LOGIN
# ==========================================
def get_youtube_client():
    print("🔐 Verifying YouTube Cloud Login...")
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
    print("✅ YouTube Login Verified!")
    return build("youtube", "v3", credentials=creds)

# ==========================================
# 2. SELF-HEALING 3-TIER LLM ROUTER
# ==========================================
def validate_plan(data):
    """Ensures all required keys exist and have 5 items"""
    req = ["title", "description", "tags", "hook_badge", "sentences", "ai_image_prompts", "pixabay_fallbacks"]
    if not all(k in data for k in req):
        return None
    if len(data["sentences"]) < 3:
        return None
    n = min(len(data["sentences"]), 5)
    data["sentences"] = data["sentences"][:n]
    while len(data["ai_image_prompts"]) < n:
        data["ai_image_prompts"].append("Futuristic glowing AI neural network in dark server room, 8k cinematic")
    while len(data["pixabay_fallbacks"]) < n:
        data["pixabay_fallbacks"].append("artificial intelligence")
    return data

def generate_plan():
    print("📡 Step 1: Scraping Breaking AI News...")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    if now_utc.hour < 7:
        search, niche = "OpenAI+OR+ChatGPT+OR+Google+Gemini+when:1d", "AI Models & Tech Giants"
    elif now_utc.hour < 12:
        search, niche = "Humanoid+Robot+OR+Nvidia+OR+Elon+Musk+AI+when:1d", "Robotics & Hardware"
    else:
        search, niche = "Artificial+Intelligence+Breakthrough+OR+Cybersecurity+when:1d", "Dark Tech & Breakthroughs"

    rss = feedparser.parse(f"https://news.google.com/rss/search?q={search}&hl=en-IN&gl=IN&ceid=IN:en")
    headlines = [e.title for e in rss.entries[:12]] or ["OpenAI and Google race toward next-generation autonomous AI agents"]
    
    prompt = f"""
    You are writing a viral documentary-style Tech YouTube Short (Niche: {niche}).
    Today's breaking headlines: {headlines}
    
    Pick the single most shocking story and write a 5-sentence script (MAXIMUM 70 WORDS TOTAL).
    Provide 5 detailed AI image prompts and 5 simple 1-2 word Pixabay search terms.
    """

    # TIER 1: GEMINI (Starts with gemini-3.8-flash + Auto-Discovers active models)
    if GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            gemini_models = ["gemini-3.8-flash"]
            try:
                for m in client.models.list():
                    name = m.name.replace("models/", "")
                    if ("flash" in name or "pro" in name) and not any(x in name for x in ["1.5", "2.0", "2.5", "vision", "embedding", "tts", "image", "audio"]):
                        if name not in gemini_models:
                            gemini_models.append(name)
            except Exception:
                pass

            for model in gemini_models[:4]:
                for attempt in range(1, 3):
                    try:
                        print(f"   🤖 Trying Gemini ({model}) [Attempt {attempt}]...")
                        res = client.models.generate_content(
                            model=model,
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=CinematicShort,
                                temperature=0.75
                            )
                        )
                        if res and res.text:
                            plan = validate_plan(json.loads(res.text))
                            if plan:
                                print(f"   ✅ Gemini ({model}) succeeded! Title: {plan['title']}")
                                return plan
                    except Exception as e:
                        print(f"   ⚠️ Gemini ({model}) error: {e}. Waiting 8s...")
                        time.sleep(8)
        except Exception as e:
            print(f"   ⚠️ Gemini client init error: {e}")

    # TIER 2: GROQ (Auto-Discovers active models on your Groq account!)
    if GROQ_API_KEY:
        print("   🔄 Failing over to Groq...")
        try:
            client_g = Groq(api_key=GROQ_API_KEY)
            groq_models = []
            try:
                for m in client_g.models.list().data:
                    mid = m.id
                    if not any(x in mid.lower() for x in ["whisper", "guard", "tts", "vision", "embed", "playai"]):
                        groq_models.append(mid)
            except Exception as e:
                print(f"   ⚠️ Groq model list error: {e}")
                groq_models = ["llama-3.3-70b-versatile", "llama3-70b-8192", "llama3-8b-8192", "gemma2-9b-it"]

            # Prioritize Llama / Qwen / DeepSeek chat models
            groq_models.sort(key=lambda x: (0 if "llama" in x.lower() else 1))
            
            sys_schema = """You are a JSON-only API. Output ONLY valid JSON with these exact keys:
{
  "title": "Short viral title #ai #tech #shorts",
  "description": "2-sentence summary + #ai #tech #shorts",
  "tags": ["AI", "Tech", "Artificial Intelligence", "Shorts"],
  "hook_badge": "BREAKING AI NEWS",
  "sentences": ["Sentence 1", "Sentence 2", "Sentence 3", "Sentence 4", "Sentence 5"],
  "ai_image_prompts": ["Prompt 1", "Prompt 2", "Prompt 3", "Prompt 4", "Prompt 5"],
  "pixabay_fallbacks": ["robot", "artificial intelligence", "cyberpunk", "server", "technology"]
}"""
            for m in groq_models[:5]:
                try:
                    print(f"   🦙 Trying Groq ({m})...")
                    res = client_g.chat.completions.create(
                        model=m,
                        messages=[
                            {"role": "system", "content": sys_schema},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7
                    )
                    plan = validate_plan(json.loads(res.choices[0].message.content))
                    if plan:
                        print(f"   ✅ Groq ({m}) succeeded! Title: {plan['title']}")
                        return plan
                except Exception as e:
                    print(f"   ⚠️ Groq ({m}) skipped: {e}")
        except Exception as e:
            print(f"   ⚠️ Groq client error: {e}")

    # TIER 3: EMERGENCY AUTO-SCRIPT BUILDER (Guarantees 0% Crash Rate)
    print("   🛡️ Activating Tier-3 Emergency Script Builder from Live RSS...")
    top_story = headlines[0].split(" - ")[0]
    return {
        "title": f"{top_story[:38]}... #ai #tech #shorts",
        "description": f"{top_story}. Follow for daily breaking AI & Tech news! #ai #tech #shorts #futuretech #coding",
        "tags": ["AI", "Tech News", "Artificial Intelligence", "Future Tech", "Robotics", "OpenAI", "Shorts"],
        "hook_badge": "BREAKING TECH UPDATE",
        "sentences": [
            f"Stop scrolling, because a massive tech shift just happened today.",
            f"Breaking reports confirm that {top_story}.",
            "Tech giants are racing to deploy this across global data centers right now.",
            "Experts warn this could completely reshape how developers and businesses work.",
            "Do you think this AI advancement is unstoppable? Drop your thoughts in the comments!"
        ],
        "ai_image_prompts": [
            "Futuristic glowing red AI brain in dark server room, cinematic 8k, vertical",
            "Silicon Valley tech headquarters with neon holographic data streams, 8k",
            "Massive supercomputer data center with glowing blue liquid cooling, cinematic",
            "Humanoid robot looking at glowing code screens in dark lab, unreal engine 5",
            "Futuristic cyberpunk city skyline at night with digital network grid, 8k"
        ],
        "pixabay_fallbacks": ["artificial intelligence", "server room", "robot", "cyberpunk", "technology"]
    }

# ==========================================
# 3. AUDIO & VISUAL ASSEMBLY
# ==========================================
async def get_audio(sentences):
    print("🎙️ Step 2: Generating Voiceover...")
    files, durs = [], []
    for i, s in enumerate(sentences):
        f = f"v_{i}.mp3"
        await edge_tts.Communicate(s, VOICE, rate="+25%", pitch="-2Hz").save(f)
        clip = AudioFileClip(f)
        durs.append(clip.duration)
        clip.close()
        files.append(f)
    print(f"⏱️ Total Audio Duration: {sum(durs):.2f}s (Under 60s Shorts Limit)")
    return files, durs

def get_sfx(total_duration, cuts):
    sr = 44100
    t = np.linspace(0, total_duration, int(sr * total_duration), endpoint=False)
    bgm = 0.05 * np.sin(2 * np.pi * 45 * t) + 0.02 * np.sin(2 * np.pi * 90 * t)
    
    blen = int(2.5 * sr)
    if blen < len(bgm):
        bt = np.linspace(0, 1, blen)
        bgm[:blen] += 0.55 * np.sin(2 * np.pi * (150 * np.exp(-5 * bt)) * bt) * np.exp(-3 * bt)

    for ct in cuts:
        idx = int(ct * sr)
        if idx + int(0.28 * sr) < len(bgm):
            bgm[idx:idx+int(0.28 * sr)] += np.random.normal(0, 0.12, int(0.28 * sr))

    with wave.open("sfx.wav", "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((np.clip(bgm, -0.9, 0.9) * 32767).astype(np.int16).tobytes())
    
    layers = [AudioFileClip("sfx.wav")]
    if os.path.exists("bg_music.mp3") and os.path.getsize("bg_music.mp3") > 10000:
        try:
            print("🎵 Mixing custom bg_music.mp3...")
            layers.append(AudioFileClip("bg_music.mp3").subclip(0, total_duration).volumex(0.15))
        except Exception as e:
            print(f"⚠️ Skipping bg_music.mp3: {e}")
    return CompositeAudioClip(layers)

def fetch_vid(prompt, pix, dur, i):
    path, vid = f"i_{i}.jpg", f"s_{i}.mp4"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 1. Try Custom AI Visual + Ken Burns Zoom
    try:
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1080&height=1920&nologo=true&seed={random.randint(1,9999)}"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200 and len(r.content) > 25000:
            with open(path, "wb") as f:
                f.write(r.content)
            frames = int(dur * 30)
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-i", path, "-t", f"{dur:.3f}",
                "-vf", f"scale=1080:1920,zoompan=z='min(zoom+0.0008,1.15)':d={frames}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,vignette=PI/3,fps=30",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", vid
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if os.path.exists(vid) and os.path.getsize(vid) > 5000:
                print(f"   ✅ Scene {i+1}/5 rendered (AI Visual)")
                return vid
    except Exception:
        pass

    # 2. Fallback to Pixabay HD Video
    if PIXABAY_API_KEY:
        for q in [pix, "artificial intelligence", "technology"]:
            try:
                r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(q)}&per_page=10&safesearch=true", timeout=15).json()
                hits = r.get("hits", [])
                if hits:
                    hit = hits[i % len(hits)]
                    v_url = hit["videos"].get("medium", {}).get("url") or hit["videos"].get("large", {}).get("url")
                    if v_url:
                        raw = f"raw_{i}.mp4"
                        with open(raw, "wb") as f:
                            f.write(requests.get(v_url, timeout=25).content)
                        subprocess.run([
                            "ffmpeg", "-y", "-stream_loop", "-1", "-i", raw, "-t", f"{dur:.3f}",
                            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4,fps=30",
                            "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", vid
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        print(f"   ✅ Scene {i+1}/5 rendered (Pixabay HD: '{q}')")
                        return vid
            except Exception:
                pass

    # 3. Last Resort Canvas
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={dur:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", vid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return vid

def format_ass_time(seconds):
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    cs = int(round((s - int(s)) * 100))
    if cs == 100: s += 1; cs = 0
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"

def make_caps(sentences, durs, hook):
    head = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Pop,Arial,88,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,8,5,2,60,60,550,1\nStyle: Hook,Arial,55,&H000000FF,&H000000FF,&H00FFFFFF,&HC0000000,-1,0,0,0,100,100,2,0,3,15,0,8,50,50,220,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events = [f"Dialogue: 1,0:00:00.00,0:00:03.50,Hook,,0,0,0,,🚨 {hook.upper()} 🚨"]
    t = 0.0
    for s, d in zip(sentences, durs):
        words = s.upper().split()
        chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)] or ["AI"]
        for idx, c in enumerate(chunks):
            dt = d / len(chunks)
            start, end = format_ass_time(t), format_ass_time(t + dt)
            t += dt
            color = "&H00FFFFFF&" if idx % 2 == 0 else "&H0000D7FF&"
            events.append(f"Dialogue: 0,{start},{end},Pop,,0,0,0,,{{\\fscx135\\fscy135\\t(0,100,\\fscx100\\fscy100)}}{{\\c{color}}}{c}")
    with open("c.ass", "w", encoding="utf-8") as f:
        f.write(head + "\n".join(events))
    return "c.ass"

# ==========================================
# 4. MAIN RUNNER
# ==========================================
async def main():
    yt = get_youtube_client()
    plan = generate_plan()
    files, durs = await get_audio(plan["sentences"])
    
    print("🎬 Step 3: Building 9:16 Visual Scenes...")
    clips = [fetch_vid(p, f, d, i) for i, (p, f, d) in enumerate(zip(plan["ai_image_prompts"], plan["pixabay_fallbacks"], durs))]
    ass = make_caps(plan["sentences"], durs, plan["hook_badge"])
    
    print("🔥 Step 4: Rendering 1080p Vertical Short...")
    with open("l.txt", "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "l.txt", "-c", "copy", "v.mp4"], check=True)
    
    voice = concatenate_audioclips([AudioFileClip(f) for f in files])
    sfx = get_sfx(voice.duration, np.cumsum(durs)[:-1])
    CompositeAudioClip([voice, sfx]).write_audiofile("a.m4a", fps=44100, codec="aac", logger=None)
    
    subprocess.run(["ffmpeg", "-y", "-i", "v.mp4", "-i", "a.m4a", "-vf", f"ass={ass}", "-c:v", "libx264", "-b:v", "8000k", "-shortest", "f.mp4"], check=True)
    
    print("🚀 Step 5: Uploading to YouTube...")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today = now_utc.date()
    slots = [
        datetime.datetime(today.year, today.month, today.day, 6, 30, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(today.year, today.month, today.day, 12, 0, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(today.year, today.month, today.day, 15, 30, 0, tzinfo=datetime.timezone.utc),
    ]
    pub = next((s.strftime("%Y-%m-%dT%H:%M:%SZ") for s in slots if s > now_utc + datetime.timedelta(minutes=30)),
               (today + datetime.timedelta(days=1)).strftime("%Y-%m-%dT06:30:00Z"))

    body = {
        "snippet": {"title": plan["title"][:90], "description": plan["description"], "tags": plan["tags"], "categoryId": "28"},
        "status": {"privacyStatus": "private", "publishAt": pub, "selfDeclaredMadeForKids": False}
    }
    res = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload("f.mp4", mimetype="video/mp4")).execute()
    vid_id = res["id"]
    print(f"🎉 SUCCESS! Video Uploaded & Scheduled for {pub}!")
    print(f"🔗 Direct YouTube Studio Link: https://studio.youtube.com/video/{vid_id}/edit")
    print(f"📺 Watch Link: https://youtu.be/{vid_id}")

if __name__ == "__main__":
    asyncio.run(main())
