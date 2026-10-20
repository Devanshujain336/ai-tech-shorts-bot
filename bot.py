# ==========================================
# 2. BULLETPROOF LLM ROUTER (GEMINI + GROQ)
# ==========================================
def generate_ai_tech_plan():
    print("📡 Step 1: Scraping AI News (Bulletproof Fallback Engine)...")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    # Topic Rotation
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
    Write a 5-sentence documentary script (max 75 words) and 5 cinematic AI image prompts for: {headlines}
    Niche: {sub_niche}. Output ONLY valid JSON.
    """

    # 1. Try Gemini with 15-second Cooldowns
    if GEMINI_API_KEY:
        client_gemini = genai.Client(api_key=GEMINI_API_KEY)
        # Try different versions of Gemini
        for model in ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro"]:
            for attempt in range(1, 3):
                try:
                    print(f"   🤖 Trying Gemini ({model}) - Attempt {attempt}...")
                    response = client_gemini.models.generate_content(
                        model=model, contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=CinematicShort, temperature=0.7)
                    )
                    if response and response.text:
                        return json.loads(response.text)
                except Exception as e:
                    print(f"   ⏳ Gemini {model} is busy. Sleeping 15s to bypass rate limit...")
                    time.sleep(15)

    # 2. Fallback to Groq (Trying multiple model names to avoid 404)
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        print("   🔄 Failing over to Groq Llama (Backup Cluster)...")
        client_groq = Groq(api_key=groq_key)
        # Try different Groq model names to ensure access
        for groq_model in ["llama-3.3-70b-specdec", "llama-3.1-70b-versatile", "llama3-70b-8192"]:
            try:
                print(f"   🦙 Trying Groq Model: {groq_model}...")
                completion = client_groq.chat.completions.create(
                    model=groq_model,
                    messages=[
                        {"role": "system", "content": "Return ONLY JSON matching CinematicShort schema."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                return json.loads(completion.choices[0].message.content)
            except Exception as e:
                print(f"   ⚠️ Groq {groq_model} not available, trying next backup...")
                continue

    raise RuntimeError("❌ All LLM providers (Gemini & Groq) are currently unavailable. Try again in 30 minutes.")
