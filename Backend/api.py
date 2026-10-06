import asyncio
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from link import Groq, generate_post_text


app = FastAPI(title="LinkPilot AI API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PostRequest(BaseModel):
    post_text: str
    image_prompt: str | None = None


class GeneratePostRequest(BaseModel):
    domain: str
    topic: str
    number_of_posts: int


@app.get("/")
async def root():
    return {
        "message": "LinkPilot AI backend is running"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


@app.post("/generate-post")
def generate_linkedin_post(request: GeneratePostRequest):
    try:
        if request.number_of_posts < 1:
            raise ValueError("number_of_posts must be at least 1.")

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")

        client = Groq(api_key=groq_api_key)
        generated_posts = []

        for day in range(1, request.number_of_posts + 1):
            post = generate_post_text(
                client,
                request.domain,
                request.topic,
                day,
            )
            fallback_post = (
                f"Sharing insights on {request.topic} in {request.domain}. "
                f"Let's connect. #Day{day}"
            )
            if post == fallback_post:
                raise RuntimeError(
                    "Groq failed to generate the post. Check the backend logs."
                )

            generated_posts.append(post)

        return {
            "success": True,
            "post": "\n\n".join(generated_posts),
        }
    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


@app.post("/post")
async def create_post(request: PostRequest):

    backend_dir = os.path.dirname(os.path.abspath(__file__))
    link_script = os.path.join(backend_dir, "link.py")

    command = [
        sys.executable,
        link_script,
        request.post_text,
    ]

    if request.image_prompt:
        command.append(request.image_prompt)

    try:

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=backend_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        stdout, _ = await process.communicate()

        output = stdout.decode("utf-8", errors="replace")

        return {
            "success": process.returncode == 0,
            "message": "LinkedIn automation completed",
            "output": output,
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e),
        }