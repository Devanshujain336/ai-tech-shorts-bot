import os
import json
import asyncio
import datetime
import urllib.parse
import textwrap
import requests
import feedparser
import numpy as np
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

# Fix MoviePy 1.0.3 compatibility with modern Pillow
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ==========================================
# 1. CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
VOICE = "en-US-ChristopherNeural"  # Crisp, authoritative tech narrator voice

class TechShortPackage(BaseModel):
    title: str = Field(description="Viral YouTube Short title under 55 chars, must end with #ai #tech #shorts")
    description: str = Field(description="2-sentence summary of the AI news + 10 viral tech hashtags")
    tags: list[str] = Field(description="8 high-volume search tags like Artificial Intelligence, AI News, Tech")
    sentences: list[str] = Field(description="Exactly 6 punchy spoken sentences forming a 40-second breaking news script. Sentence 1 MUST be a shocking hook. Sentence 6 MUST ask viewers a question for comments.")
    image_prompts: list[str] = Field(description="Exactly 6 detailed futuristic visual prompts matching each of the 6 sentences. No text in images.")

# ==========================================
# 2. SCRAPE LAST 24H BREAKING AI & TECH NEWS
# ==========================================
def generate_ai_tech_plan():
    print("📡 Step 1: Scraping breaking AI & Tech News from the last 24 hours...")
    # Pulls live AI & Tech headlines published in the last 24 hours
    rss_url = "https://news.google.com/rss/search?q=Artificial+Intelligence+OR+OpenAI+OR+Google+Gemini+OR+Robotics+OR+Nvidia+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
    feed = feedparser.parse(rss_url)
    headlines = [entry.title for entry in feed.entries[:15]]
    
    print(f"   Found {len(headlines)} breaking tech stories.")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
    You are the producer of a viral YouTube Shorts channel about Breaking AI & Tech Advancements.
    Here are the real breaking news headlines from the last 24 hours:
    {headlines}
    
    Pick the single most mind-blowing, controversial, or futuristic news story from this list.
    Write a high-retention 6-sentence script (~95 to 110 words total):
    - Sentence 1: Pattern-interrupt shock hook (e.g., "Stop scrolling, OpenAI just dropped...", "Google just changed AI forever...").
    - Sentences 2-4: Explain what just happened in simple, exciting language.
    - Sentence 5: Explain how this affects normal people, coders, or jobs.
    - Sentence 6: Ask a polarizing question to trigger comments (e.g., "Will this replace developers, or are we safe? Comment below!").
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TechShortPackage,
            temperature=0.7
        )
    )
    
    plan = json.loads(response.text)
    print(f"✅ Selected Story & Title: {plan['title']}")
    return plan

# ==========================================
# 3. GENERATE VOICEOVER PER SENTENCE (PERFECT SYNC)
# ==========================================
async def generate_sentence_audio(sentences):
    print("🎙️ Step 2: Generating synced voiceover segments...")
    audio_files = []
    for i, sentence in enumerate(sentences):
        filename = f"voice_{i}.mp3"
        communicate = edge_tts.Communicate(sentence, VOICE, rate="+12%")
        await communicate.save(filename)
        audio_files.append(filename)
    return audio_files

# ==========================================
# 4. GENERATE AI VISUALS + BURNED-IN SUBTITLES
# ==========================================
def draw_subtitle_on_image(img_path, subtitle_text):
    """Draws clean, high-contrast CapCut-style subtitles onto the 9:16 image"""
    img = PIL.Image.open(img_path).convert("RGBA").resize((1080, 1920))
    overlay = PIL.Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(overlay)
    
    # Load default Ubuntu DejaVuSans-Bold or fallback font
    try:
        font = PIL.ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
    except:
        font = PIL.ImageFont.load_default()
        
    wrapped_lines = textwrap.wrap(subtitle_text.upper(), width=24)
    y_start = 1320  # Lower-middle safe zone (above YouTube Shorts title UI)
    
    # Draw semi-transparent dark caption box
    box_height = len(wrapped_lines) * 75 + 40
    draw.rounded_rectangle(
        [(60, y_start - 25), (1020, y_start + box_height - 25)],
        radius=25,
        fill=(0, 0, 0, 190)
    )
    
    for line in wrapped_lines:
        # Draw black stroke + bright yellow/white text
        draw.text((540, y_start), line, font=font, fill=(255, 235, 59, 255), anchor="mt")
        y_start += 75
        
    combined = PIL.Image.alpha_composite(img, overlay).convert("RGB")
    combined.save(img_path)

def build_synced_video(plan, audio_files, output_file="final_short.mp4"):
    print("🎨 Step 3: Generating 9:16 AI Tech Visuals & Burning Subtitles...")
    video_clips = []
    audio_clips = []
    
    for i, (sentence, img_prompt, audio_path) in enumerate(zip(plan["sentences"], plan["image_prompts"], audio_files)):
        a_clip = AudioFileClip(audio_path)
        duration = a_clip.duration
        audio_clips.append(a_clip)
        
        # Generate 1080x1920 AI image via Pollinations Flux
        styled_prompt = f"{img_prompt}, futuristic technology, cyberpunk glow, unreal engine 5 render, 8k, vertical 9:16"
        encoded = urllib.parse.quote(styled_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&seed={i+100}"
        
        img_path = f"scene_{i}.jpg"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(img_path, "wb") as f:
                    f.write(r.content)
            else:
                raise Exception("Fallback to gradient")
        except Exception:
            # Automatic fallback dark-tech canvas if image server is busy
            fallback = PIL.Image.new("RGB", (1080, 1920), (15, 23, 42))
            fallback.save(img_path)
            
        # Apply slow zoom first, or burn subtitle cleanly
        draw_subtitle_on_image(img_path, sentence)
        
        v_clip = ImageClip(img_path).set_duration(duration).set_audio(a_clip)
        video_clips.append(v_clip)
        print(f"   Scene {i+1}/6 rendered ({duration:.1f}s)")
        
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    # Mix background music if bg_music.mp3 is in the repo
    if os.path.exists("bg_music.mp3"):
        print("🎵 Mixing background music...")
        bg = AudioFileClip("bg_music.mp3").subclip(0, final_video.duration).volumex(0.10)
        final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg]))
        
    final_video.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    return output_file

# ==========================================
# 5. SCHEDULE AT BEST TIME & UPLOAD TO YOUTUBE
# ==========================================
def get_best_publish_time():
    """Schedules for today/tomorrow at 6:00 PM IST (12:30 PM UTC)"""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    target_date = now_utc.date()
    if now_utc.hour >= 12:
        target_date += datetime.timedelta(days=1)
    publish_dt = datetime.datetime(target_date.year, target_date.month, target_date.day, 12, 30, 0)
    return publish_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def upload_to_youtube(video_path, plan):
    print("🚀 Step 4: Uploading & Scheduling to YouTube...")
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"]
    )
    creds.refresh(Request())
    youtube = build("youtube", "v3", credentials=creds)
    
    publish_at = get_best_publish_time()
    
    body = {
        "snippet": {
            "title": plan["title"][:95],
            "description": plan["description"],
            "tags": plan["tags"],
            "categoryId": "28"  # 28 = Science & Technology
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    
    print(f"🎉 SUCCESS! Video ID: {response['id']} scheduled for {publish_at} (6:00 PM IST)")

if __name__ == "__main__":
    plan = generate_ai_tech_plan()
    audio_files = asyncio.run(generate_sentence_audio(plan["sentences"]))
    video_file = build_synced_video(plan, audio_files)
    upload_to_youtube(video_file, plan)