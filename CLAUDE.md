# LinkSaver — Telegram Bot + Web UI

Personal link manager with AI auto-tagging. Share any URL to Telegram bot → AI detects tags → saved to Supabase → viewable in Next.js web UI.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Bot | Python, python-telegram-bot v20 | Webhook mode |
| Serverless | Vercel (Python functions) | Free tier, 100k req/month |
| AI Tagging | Groq API, `llama-3.1-8b-instant` | Free tier, 14k req/day |
| Link Parsing | httpx + BeautifulSoup4 | og:title, og:description, meta |
| YouTube | YouTube Data API v3 | Free, 10k units/day |
| Storage | Supabase (Postgres) | Free tier, 500MB |
| Web UI | Next.js 14 (App Router) | Deployed on same Vercel project |
| Auth | Supabase Auth | Google OAuth or magic link |

---

## Project Structure

```
/
├── api/
│   ├── webhook.py          # POST /api/webhook — Telegram updates entry point
│   └── export.py           # GET /api/export?format=md&tag=java
├── lib/
│   ├── __init__.py
│   ├── parser.py           # URL parsing: og tags, YouTube API
│   ├── tagger.py           # Groq API → returns list of tags + content type
│   └── storage.py          # Supabase client: insert, query, search
├── app/                    # Next.js App Router
│   ├── page.tsx            # Main UI: card grid with filters
│   ├── layout.tsx
│   ├── globals.css
│   └── api/
│       └── links/
│           └── route.ts    # REST API for UI (list, search, update status)
├── components/
│   ├── LinkCard.tsx        # Card: title, tags, type badge, status
│   ├── TagFilter.tsx       # Sidebar tag cloud with counts
│   └── SearchBar.tsx
├── schema.sql              # Run in Supabase SQL Editor
├── vercel.json
├── requirements.txt        # Python deps for /api
├── package.json            # Next.js deps
└── .env.example            # Copy to .env and fill in values
```

---

## Setup Steps

1. **Copy env file**: `cp .env.example .env`
2. **Supabase** — create project, run `schema.sql` in SQL Editor
3. **Groq** — get free API key at console.groq.com
4. **Telegram** — create bot via @BotFather, get token; get your user_id via @userinfobot
5. **YouTube API** — enable YouTube Data API v3 in Google Cloud Console (optional)
6. **Vercel** — `vercel deploy`, set all env vars in dashboard
7. **Register webhook**:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-app>.vercel.app/api/webhook&secret_token=<WEBHOOK_SECRET>"
   ```

---

## Bot Commands

```
/list              — last 10 links (unread first)
/list #java        — filter by tag
/search spring     — FTS search
/tags              — all tags with counts
/read <id>         — mark as read
/delete <id>       — delete link
```

## Export

```
GET /api/export?format=md         — all links as Markdown
GET /api/export?format=md&tag=java — filtered by tag
```
