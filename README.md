# AI Link Pilot

AI Link Pilot is a full-stack link library with a React + Vite frontend and a
FastAPI backend. Save links into collections, search your library, and keep
saved links between restarts with SQLite.

## Requirements

- Node.js 20.19+ or 22.12+
- Python 3.10+

## Run the backend

From the project root, create and activate a virtual environment, configure
your provider keys, then install the backend requirements:

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\Activate.ps1
Copy-Item backend\.env.example backend\.env
# Add your GROQ_API_KEY and (optionally) STABILITY_API_KEY to backend\.env
python -m pip install -r backend\requirements.txt
python -m playwright install chromium
python -m uvicorn api:app --app-dir backend --reload
```

The API runs at <http://127.0.0.1:8000>. Interactive API documentation is at
<http://127.0.0.1:8000/docs>. `GROQ_API_KEY` is required to generate posts.
`STABILITY_API_KEY` enables optional image generation; without it, publishing
continues as a text-only post.

The API provides `POST /generate-post` (`domain`, `topic`, and
`number_of_posts`) and `POST /post` (`post_text` and optional `image_prompt`).
The latter calls the LinkedIn browser automation directly and returns a
failure response if publishing is unsuccessful.

The React writing studio sends generation and publishing requests through the
Vite proxy to these FastAPI endpoints. Its generated post text comes from the
configured Groq provider.

## Publish a LinkedIn post

The API uses Playwright with a persistent browser profile in
`backend/linkedin_session` by default. Sign in to LinkedIn manually in that
profile before publishing. Set `LINKEDIN_USER_DATA_DIR` to use another profile.
Generated images are cached under `backend/image_cache`; set
`LINKPILOT_IMAGE_CACHE_DIR` to change the location. If image generation fails,
the automation logs the failure and continues with a text-only post.

This automation interacts with LinkedIn's website UI, which may change. Review
the post in the opened browser and comply with LinkedIn's terms and posting
policies.

## Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. Vite forwards `/generate-post` and `/post`
requests to the FastAPI server on port 8000.

## Frontend checks

```powershell
cd frontend
npm run lint
npm run build
```
