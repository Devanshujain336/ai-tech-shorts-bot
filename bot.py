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
# 1. CONFIGURATION
# ==========================================
GEMINI_API_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
PIXABAY_API_KEY = "".join(os.environ.get("PIXABAY_API_KEY", "").split())
VOICE = "en-US-ChristopherNeural"

class CinematicShort(BaseModel):
    title: str = Field(description="Viral YouTube Short title under 55 chars, must end with #ai #tech #shorts")
    description: str = Field(description="2-sentence summary of the AI news + 10 viral tech hashtags")
    tags: list[str] = Field(description="8 high-volume search tags")
    hook_badge: str = Field(description="3-4 word shocking headline banner for the first 3 seconds, e.g. 'SECRET AI LEAK'")
    sentences: list[str] = Field(description="Exactly 6 dramatic, documentary-style spoken sentences (~100 words total). Frame the news as a massive threat, opportunity, or secret.")
    ai_image_prompts: list[str] = Field(description="Exactly 6 highly specific, hyper-realistic image prompts. E.g., 'Sam Altman looking stressed in a dark server room, cyberpunk neon lights, 8k cinematic' or 'A glowing red AI brain consuming the internet, dystopian, hyperrealistic'. NO TEXT IN IMAGES.")
    pixabay_fallbacks: list[str] = Field(description="Exactly 6 simple 1-2 word Pixabay search terms matching each scene just in case.")

# ==========================================
# 2. ROTATING NICHE & SCRIPT GENERATION
# ==========================================
def generate_ai_tech_plan():
    print("📡 Step 1: Scraping AI News (V3 Cinematic Engine)...")
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
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    You are writing a script for a viral, documentary-style Tech YouTube Short (Niche: {sub_niche}).
    Headlines from today: {headlines}
    
    Pick the craziest story. Write a 6-sentence script that feels like a thrilling movie trailer.
    Provide 6 incredibly detailed prompts for an AI Image Generator (Midjourney style) to create visuals for each sentence. Focus on specific billionaires, glowing tech, dystopian or futuristic vibes, cinematic lighting, and intense emotions.
    """
    
    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=CinematicShort, temperature=0.8)
            )
            return json.loads(response.text)
        except Exception as e:
            time.sleep(5)
    raise RuntimeError("❌ Gemini API failed after 3 retries.")

# ==========================================
# 3. VOICE & CINEMATIC SOUND DESIGN (BOOM + SFX)
# ==========================================
async def generate_voiceover_and_timings(sentences):
    print("🎙️ Step 2: Generating documentary voiceover...")
    audio_files, durations = [], []
    for i, sentence in enumerate(sentences):
        filename = f"voice_{i}.mp3"
        communicate = edge_tts.Communicate(sentence, VOICE, rate="+15%", pitch="-2Hz") # Slightly deeper/slower for documentary feel
        await communicate.save(filename)
        clip = AudioFileClip(filename)
        durations.append(clip.duration)
        clip.close()
        audio_files.append(filename)
    return audio_files, durations

def generate_cinematic_audio(total_duration, cut_times):
    """Generates a massive cinematic BOOM at 0s, dark drone BGM, and cut whooshes"""
    sr = 44100
    t = np.linspace(0, total_duration, int(sr * total_duration), endpoint=False)
    
    # 1. Dark ambient drone (Hans Zimmer style)
    bgm = 0.08 * np.sin(2 * np.pi * 45 * t) + 0.04 * np.sin(2 * np.pi * 90 * t)
    
    # 2. Massive Cinematic BOOM on the very first frame (Shock hook)
    boom_len = int(2.5 * sr)
    if boom_len < len(bgm):
        boom_t = np.linspace(0, 1, boom_len)
        boom_env = np.exp(-3 * boom_t)
        boom_freq = 150 * np.exp(-5 * boom_t) + 30 # Drops from 180Hz to 30Hz fast
        boom_wave = 0.8 * np.sin(2 * np.pi * boom_freq * boom_t) * boom_env
        distortion = np.clip(boom_wave * 3, -0.6, 0.6) # Add gritty distortion
        bgm[:boom_len] += distortion

    # 3. Quick whooshes on cuts
    for ct in cut_times:
        idx = int(ct * sr)
        length = int(0.3 * sr)
        if idx + length < len(bgm):
            w_t = np.linspace(0, 1, length)
            env = np.sin(np.pi * w_t)
            noise = np.random.normal(0, 0.15, length) * env
            bgm[idx:idx+length] += noise
            
    bgm = np.clip(bgm, -0.95, 0.95)
    pcm = (bgm * 32767).astype(np.int16)
    with wave.open("cinematic_sfx.wav", "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return "cinematic_sfx.wav"

# ==========================================
# 4. FETCH AI ART + PIXABAY FALLBACK + KEN BURNS
# ==========================================
def fetch_ai_or_stock_video(ai_prompt, pixabay_query, duration, idx):
    """Tries to generate Custom AI Art. Falls back to Pixabay. Applies Ken Burns zoom."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    img_path = f"scene_img_{idx}.jpg"
    out_video = f"scene_vid_{idx}.mp4"
    
    # 1. Try Custom AI Image (Flux)
    success = False
    styled_prompt = f"{ai_prompt}, highly detailed, cinematic lighting, 8k resolution, unreal engine 5"
    encoded_q = urllib.parse.quote(styled_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_q}?width=1080&height=1920&nologo=true&seed={random.randint(1,9999)}"
    
    for _ in range(2):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200 and len(r.content) > 30000: # Real image is large
                with open(img_path, "wb") as f:
                    f.write(r.content)
                success = True
                break
        except:
            time.sleep(2)
            
    if success:
        # Generate Ken Burns Zoom-In effect via FFmpeg
        # zoompan slowly zooms from 1x to 1.15x over the duration
        frames = int(duration * 30)
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", img_path, "-t", f"{duration:.3f}",
            "-vf", f"scale=1080:1920,zoompan=z='min(zoom+0.0008,1.15)':d={frames}:x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2',vignette=PI/3,fps=30",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", out_video
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_video

    # 2. Fallback to Pixabay Video if AI Art generator is blocked
    print(f"   ⚠️ AI Image failed for scene {idx}, falling back to Pixabay: '{pixabay_query}'")
    video_url = None
    try:
        r = requests.get(f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={urllib.parse.quote(pixabay_query)}&safesearch=true").json()
        if r.get("hits"):
            vids = r["hits"][0].get("videos", {})
            video_url = vids.get("medium", {}).get("url") or vids.get("large", {}).get("url")
    except:
        pass

    if video_url:
        raw_file = f"raw_fb_{idx}.mp4"
        with open(raw_file, "wb") as f:
            f.write(requests.get(video_url).content)
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", raw_file, "-t", f"{duration:.3f}",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,vignette=PI/4,fps=30",
            "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", out_video
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_video
        
    # 3. Absolute Last Resort: Dark Tech Gradient
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:d={duration:.3f}", "-c:v", "libx264", out_video], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_video

def build_visuals(plan, durations):
    print("🎬 Step 3: Generating Custom Cinematic Visuals + Ken Burns Motion...")
    clips = []
    for i, (ai_prompt, pix_query, dur) in enumerate(zip(plan["ai_image_prompts"], plan["pixabay_fallbacks"], durations)):
        video_file = fetch_ai_or_stock_video(ai_prompt, pix_query, dur, i)
        clips.append(video_file)
        print(f"   ✅ Scene {i+1}/6 Rendered ({dur:.1f}s)")
    return clips

# ==========================================
# 5. DYNAMIC POP-UP CAPTIONS (.ASS)
# ==========================================
def format_ass_time(seconds):
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    cs = int(round((s - int(s)) * 100))
    if cs == 100: s += 1; cs = 0
    return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"

def create_popup_captions(sentences, durations, hook_badge):
    print("⚡ Step 4: Animating Viral Captions...")
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: PopWord,Arial,88,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,8,5,2,60,60,550,1
Style: TopBadge,Arial,55,&H000000FF,&H000000FF,&H00FFFFFF,&HC0000000,-1,0,0,0,100,100,2,0,3,15,0,8,50,50,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    # Red background badge for hook
    events.append(f"Dialogue: 1,0:00:00.00,0:00:03.50,TopBadge,,0,0,0,,🚨 {hook_badge.upper()} 🚨")
    
    current_time = 0.0
    for sentence, dur in zip(sentences, durations):
        words = sentence.strip().split()
        chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
        total_chars = sum(len(c) for c in chunks) or 1
        
        for idx, chunk in enumerate(chunks):
            chunk_dur = dur * (len(chunk) / total_chars)
            start_str, end_str = format_ass_time(current_time), format_ass_time(current_time + chunk_dur)
            
            # Colors: Alternate between White, Warning Yellow (&H0000D7FF&), and Tech Cyan (&H00FFEA00&)
            color = "&H00FFFFFF&"
            if idx % 3 == 1: color = "&H0000D7FF&" # Yellow
            elif idx % 3 == 2: color = "&H00FFEA00&" # Cyan
            
            # Intense Pop-up Zoom animation
            anim = "{\\fscx135\\fscy135\\t(0,100,\\fscx100\\fscy100)}"
            events.append(f"Dialogue: 0,{start_str},{end_str},PopWord,,0,0,0,,{anim}{{\\c{color}}}{chunk.upper()}")
            current_time += chunk_dur
            
    with open("captions.ass", "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))
    return "captions.ass"

# ==========================================
# 6. RENDER AND UPLOAD
# ==========================================
def render_and_upload(clips, audio_files, durations, plan, ass_file):
    print("🔥 Step 5: Rendering Final Cinematic Masterpiece...")
    with open("concat_list.txt", "w") as f:
        for cf in clips: f.write(f"file '{cf}'\n")
            
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt", "-c", "copy", "joined_video.mp4"], check=True)
    
    voice_clips = [AudioFileClip(af) for af in audio_files]
    full_voice = concatenate_audioclips(voice_clips)
    
    cut_times = np.cumsum(durations)[:-1]
    sfx_file = generate_cinematic_audio(full_voice.duration, cut_times)
    sfx_clip = AudioFileClip(sfx_file)
    
    final_audio = CompositeAudioClip([full_voice, sfx_clip])
    final_audio.write_audiofile("master_audio.m4a", fps=44100, codec="aac", logger=None)
    
    output_file = "final_short.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", "joined_video.mp4", "-i", "master_audio.m4a",
        "-vf", f"ass={ass_file}", "-c:v", "libx264", "-preset", "medium", "-b:v", "8000k",
        "-c:a", "aac", "-b:a", "192k", "-shortest", output_file
    ]
    subprocess.run(cmd, check=True)
    print("✅ Rendering Complete!")

    print("🚀 Step 6: Scheduling to YouTube...")
    yt = get_youtube_client()
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    today = now_utc.date()
    slots_utc = [
        datetime.datetime(today.year, today.month, today.day, 6, 30, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(today.year, today.month, today.day, 12, 0, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(today.year, today.month, today.day, 15, 30, 0, tzinfo=datetime.timezone.utc),
    ]
    publish_at = next((s.strftime("%Y-%m-%dT%H:%M:%SZ") for s in slots_utc if s > now_utc + datetime.timedelta(minutes=30)), 
                      (today + datetime.timedelta(days=1)).strftime("%Y-%m-%dT06:30:00Z"))
    
    body = {
        "snippet": {"title": plan["title"][:95], "description": plan["description"], "tags": plan["tags"], "categoryId": "28"},
        "status": {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False}
    }
    media = MediaFileUpload(output_file, chunksize=-1, resumable=True, mimetype="video/mp4")
    response = yt.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    print(f"🎉 SUCCESS! Video ID {response['id']} scheduled for {publish_at}!")

if __name__ == "__main__":
    plan = generate_ai_tech_plan()
    audio_files, durations = asyncio.run(generate_voiceover_and_timings(plan["sentences"]))
    clips = build_visuals(plan, durations)
    ass_file = create_popup_captions(plan["sentences"], durations, plan["hook_badge"])
    render_and_upload(clips, audio_files, durations, plan, ass_file)
