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

try:
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
    print("✅ Imports Successful!")
except Exception as e:
    print(f"❌ Import Error: {e}. Check your daily_short.yml pip install list.")
    exit(1)

# ==========================================
# 0. CONFIGURATION
# ==========================================
GEMINI_API_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
PIXABAY_API_KEY = "".join(os.environ.get("PIXABAY_API_KEY", "").split())
GROQ_API_KEY = "".join(os.environ.get("GROQ_API_KEY", "").split())
VOICE = "en-US-ChristopherNeural"

class CinematicShort(BaseModel):
    title: str = Field(description="Title under 55 chars #shorts")
    description: str = Field(description="Summary + hashtags")
    tags: list[str] = Field(description="8 tags")
    hook_badge: str = Field(description="3-4 word hook")
    sentences: list[str] = Field(description="5 sentences (max 75 words total)")
    ai_image_prompts: list[str] = Field(description="5 cinematic 9:16 prompts")
    pixabay_fallbacks: list[str] = Field(description="5 search terms")

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
    return build("youtube", "v3", credentials=creds)

# ==========================================
# 2. THE LLM ROUTER (GEMINI + GROQ)
# ==========================================
def generate_plan():
    print("📡 Scraping Breaking News & Generating Script...")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    # Topic Rotation based on time of day
    if now_utc.hour < 7:
        search, niche = "OpenAI+OR+ChatGPT+OR+Google+Gemini+when:1d", "AI Models"
    elif now_utc.hour < 12:
        search, niche = "Humanoid+Robot+OR+Nvidia+OR+Elon+Musk+AI+when:1d", "Robotics"
    else:
        search, niche = "AI+Breakthrough+OR+Cyber+Security+when:1d", "Breakthroughs"

    rss = feedparser.parse(f"https://news.google.com/rss/search?q={search}&hl=en-IN&gl=IN&ceid=IN:en")
    headlines = [e.title for e in rss.entries[:10]]
    prompt = f"Write a 5-sentence doc script (<75 words) and 5 image prompts for: {headlines}. Niche: {niche}. Output ONLY JSON."

    # TRY GEMINI
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        for model in ["gemini-1.5-flash", "gemini-2.0-flash-exp"]:
            try:
                print(f"   🤖 Trying Gemini ({model})...")
                res = client.models.generate_content(
                    model=model, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=CinematicShort)
                )
                if res and res.text: return json.loads(res.text)
            except: 
                print(f"   ⏳ Gemini {model} busy, waiting 5s...")
                time.sleep(5)

    # TRY GROQ
    if GROQ_API_KEY:
        print("   🔄 Failing over to Groq...")
        client_g = Groq(api_key=GROQ_API_KEY)
        for m in ["llama-3.3-70b-specdec", "llama-3.1-70b-versatile"]:
            try:
                print(f"   🦙 Trying Groq ({m})...")
                res = client_g.chat.completions.create(
                    model=m, messages=[{"role": "system", "content": "Return JSON."}, {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                return json.loads(res.choices[0].message.content)
            except: continue
    
    raise RuntimeError("❌ All LLM providers failed.")

# ==========================================
# 3. AUDIO & VISUAL ASSEMBLY
# ==========================================
async def get_audio(sentences):
    print("🎙️ Generating Voiceover...")
    files, durs = [], []
    for i, s in enumerate(sentences):
        f = f"v_{i}.mp3"
        await edge_tts.Communicate(s, VOICE, rate="+25%", pitch="-2Hz").save(f)
        clip = AudioFileClip(f)
        durs.append(clip.duration)
        clip.close()
        files.append(f)
    return files, durs

def get_sfx(total_duration, cuts):
    sr = 44100
    t = np.linspace(0, total_duration, int(sr * total_duration), endpoint=False)
    bgm = 0.05 * np.sin(2 * np.pi * 45 * t)
    # Boom at start
    blen = int(2.5 * sr)
    if blen < len(bgm):
        bt = np.linspace(0, 1, blen)
        bgm[:blen] += 0.5 * np.sin(2 * np.pi * (150 * np.exp(-5 * bt)) * bt) * np.exp(-3 * bt)
    
    with wave.open("sfx.wav", "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((np.clip(bgm, -0.9, 0.9) * 32767).astype(np.int16).tobytes())
    
    layers = [AudioFileClip("sfx.wav")]
    if os.path.exists("bg_music.mp3") and os.path.getsize("bg_music.mp3") > 10000:
        layers.append(AudioFileClip("bg_music.mp3").subclip(0, total_duration).volumex(0.15))
    return CompositeAudioClip(layers)

def fetch_vid(prompt, pix, dur, i):
    path, vid = f"i_{i}.jpg", f"s_{i}.mp4"
    try:
        r = requests.get(f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1080&height=1920&nologo=true", timeout=20)
        with open(path, "wb") as f: f.write(r.content)
        frames = int(dur * 30)
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", path, "-t", f"{dur:.3f}", "-vf", f"scale=1080:1920,zoompan=z='min(zoom+0.0008,1.15)':d={frames}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':s=1080x1920,vignette=PI/3,fps=30", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", vid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return vid
    except:
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={dur:.3f}", vid], stdout=subprocess.DEVNULL)
        return vid

def make_caps(sentences, durs, hook):
    head = "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Pop,Arial,90,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,8,5,2,60,60,550,1\nStyle: Hook,Arial,55,&H000000FF,&H000000FF,&H00FFFFFF,&HC0000000,-1,0,0,0,100,100,2,0,3,15,0,8,50,50,220,1\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    events = [f"Dialogue: 1,0:00:00.00,0:00:03.50,Hook,,0,0,0,,🚨 {hook.upper()} 🚨"]
    t = 0.0
    for s, d in zip(sentences, durs):
        chunks = [" ".join(s.upper().split()[i:i+2]) for i in range(0, len(s.split()), 2)]
        for c in chunks:
            start = f"0:00:{int(t):02d}.{int((t%1)*100):02d}"
            t += d/len(chunks)
            end = f"0:00:{int(t):02d}.{int((t%1)*100):02d}"
            events.append(f"Dialogue: 0,{start},{end},Pop,,0,0,0,,{{\\fscx130\\fscy130\\t(0,100,\\fscx100\\fscy100)}}{c}")
    with open("c.ass", "w") as f: f.write(head + "\n".join(events))
    return "c.ass"

# ==========================================
# 4. MAIN RUNNER
# ==========================================
async def main():
    try:
        plan = generate_plan()
        files, durs = await get_audio(plan["sentences"])
        clips = [fetch_vid(p, f, d, i) for i, (p, f, d) in enumerate(zip(plan["ai_image_prompts"], plan["pixabay_fallbacks"], durs))]
        ass = make_caps(plan["sentences"], durs, plan["hook_badge"])
        
        print("🔥 Rendering Video...")
        with open("l.txt", "w") as f:
            for c in clips: f.write(f"file '{c}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "l.txt", "-c", "copy", "v.mp4"], check=True)
        
        voice = concatenate_audioclips([AudioFileClip(f) for f in files])
        sfx = get_sfx(voice.duration, np.cumsum(durs)[:-1])
        CompositeAudioClip([voice, sfx]).write_audiofile("a.m4a", fps=44100, codec="aac")
        
        subprocess.run(["ffmpeg", "-y", "-i", "v.mp4", "-i", "a.m4a", "-vf", "ass=c.ass", "-c:v", "libx264", "-b:v", "8000k", "-shortest", "f.mp4"], check=True)
        
        print("🚀 Uploading...")
        yt = get_youtube_client()
        pub = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = {"snippet": {"title": plan["title"][:90], "description": plan["description"], "categoryId": "28"}, "status": {"privacyStatus": "private", "publishAt": pub}}
        yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload("f.mp4", mimetype="video/mp4")).execute()
        print(f"🎉 Success! Video scheduled for {pub}")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
