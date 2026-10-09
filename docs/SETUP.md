# Detailed Setup Guide — Voice Agent (Free Tier)

## 1. Get Free API Keys

### Groq (LLM) — Recommended
1. Go to https://console.groq.com
2. Sign up / log in
3. Create an API key
4. Copy it into `backend/.env` as `GROQ_API_KEY`

### AssemblyAI (STT) — Optional but good
1. https://www.assemblyai.com
2. Free tier gives you credits every month
3. Put the key in `ASSEMBLYAI_API_KEY`

You can also skip cloud STT and use the **browser’s built-in Speech Recognition** (already implemented in the frontend). It works well in Chrome/Edge and is completely free.

### Supabase (optional)
1. https://supabase.com → New project
2. Copy Project URL + anon key
3. Create a storage bucket named `documents`

---

## 2. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set GROQ_API_KEY
```

Run:
```bash
python -m app.main
```

You should see the server start on http://localhost:7860

Test health:
```bash
curl http://localhost:7860/health
```

---

## 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
# NEXT_PUBLIC_BACKEND_URL=http://localhost:7860
```

Run:
```bash
npm run dev
```

Open http://localhost:3000

---

## 4. First Conversation

1. Allow microphone access when the browser asks
2. Click the microphone button and speak, **or** type a message
3. Try:
   - “What time is it?”
   - “Calculate 17 * 24”
   - Upload a PDF → “What is this document about?”
   - “Read the document” / “Dictate the file”

---

## 5. Deploy (Free)

### Frontend → Vercel
- Push `frontend/` to GitHub
- Import in Vercel
- Set environment variable `NEXT_PUBLIC_BACKEND_URL` to your backend public URL

### Backend → Railway / Render / Fly.io
- Create a new web service
- Root directory: `backend`
- Start command: `python -m app.main`
- Add all environment variables from `.env`
- Expose port 7860

### Important for WebSockets
Make sure your hosting provider supports WebSockets (Railway and Render do on free/paid plans).

---

## 6. Troubleshooting

| Problem                        | Solution                                      |
|--------------------------------|-----------------------------------------------|
| “Could not reach the backend”  | Make sure backend is running on port 7860     |
| Microphone not working         | Use Chrome or Edge, allow mic permission      |
| No TTS audio                   | Browser may block autoplay — click once first |
| Groq rate limit                | Wait a minute or switch model                 |
| Document upload fails          | Check file type (PDF, DOCX, TXT, MD)          |

---

## Next Improvements You Can Ask Me For

- Full Pipecat real-time streaming pipeline
- Better interruption / barge-in handling
- Supabase auth + multi-user
- Better document section detection
- Docker Compose for one-command local start
- Mobile-friendly PWA
