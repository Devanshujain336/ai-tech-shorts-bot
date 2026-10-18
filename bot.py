import os
import json
import wave
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
    print("✅ YouTube Login Verified!")
    return build("youtube", "v3", credentials=creds)

# ==========================================
# 1. CONFIGURATION
# ==========================================
GEMINI_API_KEY = "".join(os.environ.get("GEMINI_API_KEY", "").split())
PIXABAY_API_KEY = "".join(os.environ.get("PIXABAY_API_KEY", "").split())
VOICE = "en-US-ChristopherNeural"

class TechShortPackage(BaseModel):
    title: str = Field(description="Viral YouTube Short title under 55 chars, must end with #ai #tech #shorts")
    description: str = Field(description="2-sentence summary of the AI news + 10 viral tech hashtags")
    tags: list[str] = Field(description="8 high-volume search tags like Artificial Intelligence, AI News, Tech")
    hook_badge: str = Field(description="3-4 word shocking headline banner for the first 3 seconds, e.g. 'OPENAI SECRET LEAK'")
    sentences: list[str] = Field(description="Exactly 6 fast-paced, high-retention spoken sentences (~100 words total). Sentence 1 = shocking hook. Sentence 6 = controversial question for comments.")
    pixabay_queries: list[str] = Field(description="Exactly 12 simple 1-to-2 word search queries for Pixabay tech videos/animations (2 per sentence), e.g. 'artificial intelligence', 'robot', 'cyberpunk', 'circuit board', 'data', 'hacker', 'futuristic', 'matrix', 'neural network', 'space', 'coding', 'technology'")

# ==========================================
# 2. SCRAPE BREAKING AI NEWS & WRITE SCRIPT
# ==========================================
def generate_ai_tech_plan():
    print("📡 Step 1: Scraping breaking AI & Tech News...")
    rss_url = "https://news.google.com/rss/search?q=Artificial+Intelligence+OR+OpenAI+OR+Google+Gemini+OR+Robotics+OR+Nvidia+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    headlines = [entry.title for entry in feed.entries[:15]]
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    You are the producer of a viral 1M+ view YouTube Shorts channel covering Breaking AI & Tech News.
    Breaking headlines from the last 24 hours:
    {headlines}
    
    Pick the single most shocking or exciting story. Write a 6-sentence fast-paced script:
    - Sentence 1: Aggressive pattern-interrupt hook ("Stop scrolling! ...", "Nobody is talking about what just happened in AI...").
    - Sentences 2-4: High-energy breakdown of the news.
    - Sentence 5: Why this changes everything.
    - Sentence 6: Debate question forcing viewers to comment.
    Also provide 12 simple 1-to-2 word search queries for Pixabay videos (like 'robot', 'coding', 'data', 'cyberpunk', 'circuit', 'artificial intelligence').
    """
    
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TechShortPackage,
            temperature=0.75
        )
    )
    plan = json.loads(response.text)
    print(f"✅ Viral Title: {plan['title']}")
    return plan

# ==========================================
# 3. VOICEOVER + SOUND EFFECTS + BG BEAT
# ==========================================
async def generate_voiceover_and_timings(sentences):
    print("🎙️ Step 2: Generating high-energy voiceover...")
    audio_files = []
    durations = []
    for i, sentence in enumerate(sentences):
        filename = f"voice_{i}.mp3"
        communicate = edge_tts.Communicate(sentence, VOICE, rate="+18%", pitch="+2Hz")
        await communicate.save(filename)
        clip = AudioFileClip(filename)
        durations.append(clip.duration)
        clip.close()
        audio_files.append(filename)
    return audio_files, durations

def generate_sfx_and_bgm(total_duration, cut_times):
    """Generates transition whooshes on every cut + a dark cyberpunk bass pulse"""
    sr = 44100
    t = np.linspace(0, total_duration, int(sr * total_duration), endpoint=False)
    beat_env = 0.5 + 0.5 * np.sin(2 * np.pi * (110 / 60) * t)
    bgm = 0.06 * np.sin(2 * np.pi * 55 * t) * beat_env + 0.03 * np.sin(2 * np.pi * 110 * t)
    
    for ct in cut_times:
        idx = int(ct * sr)
        length = int(0.28 * sr)
        if idx + length < len(bgm):
            w_t = np.linspace(0, 1, length)
            env = np.sin(np.pi * w_t)
            noise = np.random.normal(0, 0.12, length) * env
            sweep = 0.15 * np.sin(2 * np.pi * (180 - 120 * w_t) * w_t) * env
            bgm[idx:idx+length] += (noise + sweep)
            
    bgm = np.clip(bgm, -0.95, 0.95)
    pcm = (bgm * 32767).astype(np.int16)
    with wave.open("auto_sfx_bgm.wav", "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return "auto_sfx_bgm.wav"

# ==========================================
# 4. DOWNLOAD 12 HD TECH VIDEOS (PIXABAY API)
# ==========================================
def download_12_pixabay_clips(queries, durations):
    print("🎬 Step 3: Downloading 12 Fast-Cut HD Tech & 3D Animation Clips from Pixabay...")
    fallback_queries = [
        "artificial intelligence", "robot", "cyberpunk", "circuit board",
        "futuristic", "matrix", "hacker", "data", "technology",
        "network", "computer", "digital"
    ]
    
    used_ids = set()
    processed_clips = []
    
    # 2 fast video cuts per sentence (12 cuts total = new clip every ~3 seconds!)
    clip_durations = []
    for d in durations:
        clip_durations.append(d / 2.0)
        clip_durations.append(d / 2.0)
        
    for i in range(12):
        q = queries[i] if i < len(queries) else fallback_queries[i % len(fallback_queries)]
        dur = clip_durations[i]
        video_url = None
        
        for search_term in [q, fallback_queries[i % len(fallback_queries)], "technology"]:
            encoded_q = urllib.parse.quote(search_term)
            url = f"https://pixabay.com/api/videos/?key={PIXABAY_API_KEY}&q={encoded_q}&per_page=15&safesearch=true"
            try:
                r = requests.get(url, timeout=15).json()
                for hit in r.get("hits", []):
                    if hit["id"] not in used_ids:
                        used_ids.add(hit["id"])
                        vids = hit.get("videos", {})
                        # Prefer medium (720p/1080p fast download) or large
                        video_url = (
                            vids.get("medium", {}).get("url")
                            or vids.get("large", {}).get("url")
                            or vids.get("small", {}).get("url")
                        )
                        if video_url:
                            break
            except Exception as e:
                print(f"   Pixabay search retry for '{search_term}': {e}")
            if video_url:
                break
                
        raw_file = f"raw_{i}.mp4"
        norm_file = f"norm_{i}.mp4"
        with open(raw_file, "wb") as f:
            f.write(requests.get(video_url, timeout=30).content)
            
        # FFmpeg: Center-crop to 1080x1920 9:16 vertical + vibrant color boost + 30fps
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", raw_file,
            "-t", f"{dur:.3f}",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.10:saturation=1.25,fps=30",
            "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", norm_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        processed_clips.append(norm_file)
        print(f"   ✅ Cut {i+1}/12 ready ({dur:.1f}s) - '{q}'")
        
    return processed_clips

# ==========================================
# 5. HORMOZI / MRBEAST POP-UP ANIMATED CAPTIONS (.ASS)
# ==========================================
def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def create_popup_captions_ass(sentences, durations, hook_badge, ass_file="captions.ass"):
    print("⚡ Step 4: Creating 2-Word Pop-Up Animated Captions...")
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: PopWord,DejaVu Sans,84,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,8,4,2,60,60,550,1
Style: TopBadge,DejaVu Sans,52,&H0000EBFF,&H000000FF,&H00000000,&HC0000000,-1,0,0,0,100,100,2,0,3,18,0,8,50,50,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    events.append(f"Dialogue: 1,0:00:00.00,0:00:03.50,TopBadge,,0,0,0,,🚨 {hook_badge.upper()} 🚨")
    
    current_time = 0.0
    for sentence, dur in zip(sentences, durations):
        words = sentence.strip().split()
        chunks = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
        total_chars = sum(len(c) for c in chunks) or 1
        
        for idx, chunk in enumerate(chunks):
            chunk_dur = dur * (len(chunk) / total_chars)
            start_str = format_ass_time(current_time)
            end_str = format_ass_time(current_time + chunk_dur)
            
            parts = chunk.upper().split()
            if len(parts) == 2:
                color = "&H0000EBFF&" if idx % 2 == 0 else "&H00FFF000&"
                styled_text = f"{parts[0]} {{\\c{color}}}{parts[1]}"
            else:
                styled_text = f"{{\\c&H0000EBFF&}}{parts[0]}"
                
            anim = "{\\fscx125\\fscy125\\t(0,90,\\fscx100\\fscy100)}"
            events.append(f"Dialogue: 0,{start_str},{end_str},PopWord,,0,0,0,,{anim}{styled_text}")
            current_time += chunk_dur
            
    with open(ass_file, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))
    return ass_file

# ==========================================
# 6. ASSEMBLE FINAL 1080P 30FPS HIGH-BITRATE SHORT
# ==========================================
def render_viral_short(clip_files, audio_files, durations, ass_file, output_file="final_short.mp4"):
    print("🔥 Step 5: Rendering 1080p 30FPS High-Bitrate Short with FFmpeg...")
    with open("concat_list.txt", "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf}'\n")
            
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat_list.txt", "-c", "copy", "joined_video.mp4"], check=True)
    
    voice_clips = [AudioFileClip(af) for af in audio_files]
    full_voice = concatenate_audioclips(voice_clips)
    
    cut_times = np.cumsum([d / 2.0 for d in durations for _ in range(2)])[:-1]
    sfx_file = generate_sfx_and_bgm(full_voice.duration, cut_times)
    sfx_clip = AudioFileClip(sfx_file)
    
    layers = [full_voice, sfx_clip]
    if os.path.exists("bg_music.mp3") and os.path.getsize("bg_music.mp3") > 10000:
        try:
            bg = AudioFileClip("bg_music.mp3").subclip(0, full_voice.duration).volumex(0.12)
            layers.append(bg)
        except Exception as e:
            print(f"⚠️ Skipping invalid bg_music.mp3 ({e}), using built-in cyber beat.")
        
    final_audio = CompositeAudioClip(layers)
    final_audio.write_audiofile("master_audio.m4a", fps=44100, codec="aac")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", "joined_video.mp4",
        "-i", "master_audio.m4a",
        "-vf", f"ass={ass_file}",
        "-c:v", "libx264", "-preset", "medium", "-b:v", "8000k",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", output_file
    ]
    subprocess.run(cmd, check=True)
    print("✅ High-Retention Viral Short Rendered!")
    return output_file

# ==========================================
# 7. SCHEDULE & UPLOAD TO YOUTUBE
# ==========================================
def get_best_publish_time():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    target_date = now_utc.date()
    if now_utc.hour >= 12:
        target_date += datetime.timedelta(days=1)
    publish_dt = datetime.datetime(target_date.year, target_date.month, target_date.day, 12, 30, 0)
    return publish_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def upload_to_youtube(youtube, video_path, plan):
    print("🚀 Step 6: Uploading & Scheduling to YouTube...")
    publish_at = get_best_publish_time()
    body = {
        "snippet": {
            "title": plan["title"][:95],
            "description": plan["description"],
            "tags": plan["tags"],
            "categoryId": "28"
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False
        }
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    response = youtube.videos().insert(part="snippet,status", body=body, media_body=media).execute()
    print(f"🎉 SUCCESS! Video ID: {response['id']} scheduled for {publish_at}")

if __name__ == "__main__":
    yt = get_youtube_client()
    plan = generate_ai_tech_plan()
    audio_files, durations = asyncio.run(generate_voiceover_and_timings(plan["sentences"]))
    clips = download_12_pixabay_clips(plan["pixabay_queries"], durations)
    ass_file = create_popup_captions_ass(plan["sentences"], durations, plan["hook_badge"])
    final_video = render_viral_short(clips, audio_files, durations, ass_file)
    upload_to_youtube(yt, final_video, plan)
