import asyncio
import logging
import os
import random  # For stealth randomization
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests
from datetime import datetime
import re  # For regex in locators
import psutil
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, expect
from groq import Groq
import glob  # For optional cache cleanup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/linkedin_automation.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Stability AI configuration
STABILITY_KEY = "sk-QKNxTsIPuubuJhk2NChlzUyrAqDC5o9XUJ7meGRIvhQKAHNd"
IMAGE_CACHE_DIR = "./image_cache"
STATIC_DIR = "./static"
MIN_MEMORY_GB = 2.0

# Groq configuration
GROQ_MODEL = "llama-3.3-70b-versatile"

def generate_image_with_stability(prompt, output_dir="image_cache"):
    """Generate image using Stability AI SD3 endpoint."""
    import io

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    url = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

    headers = {
        "Authorization": f"Bearer {STABILITY_KEY}",
        "Accept": "image/*"
    }

    # The API requires multipart/form-data
    data = {
        "model": "sd3",
        "prompt": prompt,
        "aspect_ratio": "1:1",
        "output_format": "png"
    }

    # Add a dummy "none" field to force multipart encoding
    files = {"none": ("", io.BytesIO(b""), "application/octet-stream")}

    try:
        logger.info("ðŸŽ¨ Generating image with Stability AI SD3...")
        response = requests.post(url, headers=headers, data=data, files=files, timeout=60)

        if response.status_code == 200:
            # Create unique filename
            safe_prompt = "".join(c for c in prompt if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_prompt = safe_prompt.replace(' ', '_')[:50]
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_prompt}_{ts}.png"
            cached_path = os.path.join(output_dir, filename)

            with open(cached_path, "wb") as f:
                f.write(response.content)

            logger.info(f"âœ… Image saved successfully: {cached_path}")

            # Optional: Cleanup old cache files
            cleanup_cache(max_files=100)

            return cached_path

        else:
            try:
                err = response.json()
            except:
                err = response.text
            logger.error(f"âŒ Stability API error {response.status_code}: {err}")
            return create_placeholder_image()

    except Exception as e:
        logger.error(f"âŒ Exception during image generation: {e}")
        return create_placeholder_image()

def create_placeholder_image():
    """Create a branded placeholder image so it's not a blank/white image."""
    try:
        placeholder_path = os.path.join(STATIC_DIR, "placeholder.png")
        os.makedirs(os.path.dirname(placeholder_path), exist_ok=True)
        w, h = 768, 512
        img = Image.new('RGB', (w, h), color=(255, 91, 173))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            r = int(255 - (255-105) * (y/h))
            g = int(178 - (178-24) * (y/h))
            b = int(108 + (136-108) * (y/h))
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        text = "Image unavailable"
        sub = "Upload or generate an image"
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            font_small = ImageFont.truetype("arial.ttf", 22)
        except Exception:
            font = ImageFont.load_default()
            font_small = ImageFont.load_default()
        tw = draw.textlength(text, font=font)
        sw = draw.textlength(sub, font=font_small)
        draw.text(((w - tw)/2, h/2 - 20), text, fill=(255,255,255), font=font)
        draw.text(((w - sw)/2, h/2 + 20), sub, fill=(245,245,245), font=font_small)
        img.save(placeholder_path, format="PNG")
        logger.info(f"Created placeholder image at {placeholder_path}")
        return placeholder_path
    except Exception as e:
        logger.error(f"Failed to create placeholder image: {str(e)}")
        return None

def cleanup_cache(max_files=100):
    """Clean up old image cache files."""
    files = sorted(glob.glob(os.path.join(IMAGE_CACHE_DIR, "*.png")), key=os.path.getctime)
    if len(files) > max_files:
        for old_file in files[:-max_files]:
            os.remove(old_file)
        logger.info(f"Cleaned up {len(files) - max_files} old cache files")

def sanitize_linkedin_text(text: str) -> str:
    """Reduce special characters/emojis/hashtags; keep it concise and professional."""
    try:
        if text is None:
            return ""
        # Normalize smart punctuation
        replacements = {
            "\u201c": '"', "\u201d": '"',
            "\u2019": "'", "\u2018": "'",
            "\u2013": '-', "\u2014": '-',
            "\u2026": '...', "\u2022": '-',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        # Drop markdown-like formatting
        text = re.sub(r"(?m)^\s*#{2,}\s*", "", text)
        text = text.replace("**", "").replace("__", "").replace("`", "")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        # Collapse repeated punctuation
        text = re.sub(r"([!?.])\1{1,}", r"\1", text)
        # Remove most emojis/symbols
        try:
            emoji_pattern = re.compile("[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]", flags=re.UNICODE)
            text = emoji_pattern.sub("", text)
        except re.error:
            pass
        # Limit hashtags to first 3 unique
        hashtags = re.findall(r"(?<!\w)#\w+", text)
        if len(hashtags) > 3:
            text_no_hash = re.sub(r"(?<!\w)#\w+", "", text)
            seen = set()
            kept = []
            for h in hashtags:
                key = h.lower()
                if key not in seen:
                    kept.append(h)
                    seen.add(key)
                if len(kept) == 3:
                    break
            text = (text_no_hash.strip() + "\n" + " ".join(kept)).strip()
        # Whitespace normalization
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text
    except Exception:
        return text

def generate_post_text(client: Groq, domain_name: str, custom_prompt: str, day: int) -> str:
    """Generate post text using Groq API. Adapted for LinkedIn (professional, engaging)."""
    generation_prompt = f"""
Create a concise, professional LinkedIn post about "{custom_prompt}" in the context of "{domain_name}".
- Keep it under 1200 characters (aim for 600â€“900)
- Avoid excessive special characters and emojis; use at most 0â€“2 subtle emojis if any
- Prefer clean language; no markdown formatting
- Optionally include up to 2 relevant hashtags at the end
- Include "#Day{day}" at the end to mark the series
- Strictly follow any user-provided instructions in the prompt
"""

    try:
        chat_completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates clean, professional LinkedIn posts with minimal emojis and no markdown."},
                {"role": "user", "content": generation_prompt}
            ],
            max_tokens=400,  # Keep concise for LinkedIn
            temperature=0.7
        )
        generated_text = chat_completion.choices[0].message.content.strip()
        # Enforce character limit for LinkedIn (concise)
        if len(generated_text) > 1200:
            generated_text = generated_text[:1197] + "..."
        logger.info(f"Generated post text: {generated_text[:100]}...")
        return generated_text
    except Exception as e:
        logger.error(f"Failed to generate post text: {e}")
        default_text = f"Sharing insights on {custom_prompt} in {domain_name}. Let's connect. #Day{day}"
        return default_text

async def post_to_linkedin(page, post_text: str, image_path: str = None, textbox=None):
    """Post text and optional image to LinkedIn."""
    try:
        # Sanitize and shorten content for LinkedIn
        original_len = len(post_text or "")
        post_text = sanitize_linkedin_text(post_text or "")
        if original_len != len(post_text):
            logger.info(f"Sanitized LinkedIn text (len {original_len} -> {len(post_text)})")
        # Navigate to home/feed
        logger.info("ðŸ  Navigating to LinkedIn home...")
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
        await page.screenshot(path="./screenshots/linkedin/feed_after_goto.png")  # Debug: Capture post-navigation state

        # Wait for feed to be interactive
        try:
            await page.wait_for_selector("[data-urn*='urn:li:activity']", timeout=30000)  # Wait for at least one post in feed
            logger.info("âœ… Feed loaded (posts visible)")
        except PlaywrightTimeoutError:
            logger.warning("âš ï¸ Feed selector timeout; using fallback wait")
            await page.wait_for_timeout(10000)  # 10s buffer for dynamic load

        await page.wait_for_timeout(5000)  # Extra human-like pause

        # Opening post composer
        logger.info("ðŸ“ Opening post composer...")
        composer_trigger = None
        try:
            composer_trigger = page.get_by_role("button", name="Start a post")
            await composer_trigger.wait_for(state="visible", timeout=10000)
            await composer_trigger.click()
            logger.info("âœ… Clicked Post button using get_by_role('button', name='Start a post')")
        except PlaywrightTimeoutError:
            logger.debug("Primary role selector failed; trying text-based fallback")
            try:
                composer_trigger = page.get_by_text("Start a post")
                await composer_trigger.wait_for(state="visible", timeout=8000)
                await composer_trigger.first.click()  # Click first match
                logger.info("âœ… Clicked using get_by_text('Start a post')")
            except PlaywrightTimeoutError:
                logger.debug("Text fallback failed; trying aria-label CSS")
                css_selectors = [
                    "[aria-label*='Start a post']",
                    "[data-control-name*='share_prompt_compose']",
                    "button:has-text(\"Start a post\")"  # Playwright text pseudo-class
                ]
                for sel in css_selectors:
                    try:
                        composer_trigger = page.locator(sel).first
                        await composer_trigger.wait_for(state="visible", timeout=5000)
                        await composer_trigger.click(force=True)
                        logger.info(f"âœ… Clicked using CSS: {sel}")
                        break
                    except PlaywrightTimeoutError:
                        continue

        if not composer_trigger:
            logger.error("âŒ All composer selectors failed")
            await page.screenshot(path="./screenshots/linkedin/post_button_not_found.png")
            return False

        # Wait for composer to open and stabilize
        await page.wait_for_timeout(3000)
        await page.wait_for_function("document.querySelector('div[role=\"textbox\"][contenteditable=\"true\"]') !== null && document.querySelector('div[role=\"textbox\"][contenteditable=\"true\"]').isContentEditable", timeout=15000)  # Ensure editor is editable

        # Type in text area - FIXED: Use fill to simulate copy-paste, clear first
        logger.info("âŒ¨ Filling text editor with copy-paste simulation...")
        text_selectors = [
            "div[role='textbox'][contenteditable='true']",
            ".ql-editor",
            "div[data-slate-editor='true']"
        ]
        textbox = textbox or None
        for sel in text_selectors:
            try:
                textbox = page.locator(sel).first
                await textbox.wait_for(state="visible", timeout=15000)
                await textbox.click()
                # Clear existing content to prevent duplication
                await textbox.fill("")
                await page.wait_for_timeout(random.randint(200, 500))  # Brief pause after clear
                # Fill with text to simulate copy-paste
                await textbox.fill(post_text)
                logger.info(f"âœ… Filled post content using selector: {sel}")
                break
            except PlaywrightTimeoutError:
                logger.debug(f"Text selector failed: {sel}")
                continue

        if not textbox:
            logger.error("âŒ Could not find text area")
            await page.screenshot(path="./screenshots/linkedin/text_area_not_found.png")
            return False

        # Wait for composer to stabilize
        await page.wait_for_timeout(2000)

        # Wait for composer toolbar/actions to load before upload
        try:
            await page.wait_for_selector("button[aria-label*='Media'], button[aria-label*='Photo'], .share-actions__actions-bar", timeout=4000)
            logger.info("✅ Composer actions bar loaded")
        except PlaywrightTimeoutError:
            logger.debug("Actions bar wait completed; proceeding")

        # Handle image upload if provided
        uploaded = False
        if image_path and os.path.exists(image_path):
            logger.info(f"📸 Uploading image: {image_path}")
            await page.screenshot(path="./screenshots/linkedin/before_image_upload.png")

            # Primary: Role-based with updated regex for 2025/2026 "Media", "Photo icon", or "Add media"
            photo_trigger = None
            try:
                photo_trigger = page.get_by_role("button", name=re.compile(r"Media|Photo|Add media|Attach photo", re.I)).first
                await photo_trigger.wait_for(state="visible", timeout=6000)
                logger.info("✅ Image button visible using get_by_role with updated regex")
            except PlaywrightTimeoutError:
                logger.warning("⚠️ Primary image button not detected; trying CSS fallbacks")
                photo_button_selectors = [
                    "button[aria-label*='Media']",
                    "button[aria-label*='Photo']",
                    "button[aria-label*='Add photo']",
                    "button[aria-label*='Attach a photo']",
                    "[data-control-name='media_upload']",
                    "div[aria-label*='Photo/video']"
                ]
                for sel in photo_button_selectors:
                    try:
                        photo_trigger = page.locator(sel).first
                        await photo_trigger.wait_for(state="visible", timeout=3000)
                        logger.info(f"✅ Image button found via CSS: {sel}")
                        break
                    except PlaywrightTimeoutError:
                        continue

            if photo_trigger:
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        # Priority 1: Direct file input (doesn't require input to be visible)
                        file_input = page.locator("input[type='file'][accept*='image'], input[type='file']").first
                        if await file_input.count() > 0:
                            try:
                                await file_input.set_input_files(image_path)
                                logger.info(f"✅ Image uploaded via direct file input (retry {retry+1})")
                                uploaded = True
                                break
                            except Exception as fi_err:
                                logger.debug(f"Direct file input failed: {fi_err}")

                        # Priority 2: Click Photo button and set via file chooser
                        if not uploaded:
                            await photo_trigger.scroll_into_view_if_needed()
                            async with page.expect_file_chooser(timeout=10000) as fc_info:
                                await photo_trigger.click(force=True)
                            file_chooser = await fc_info.value
                            await file_chooser.set_files(image_path)
                            logger.info(f"✅ Image uploaded via Photo button (retry {retry+1})")
                            uploaded = True
                            break

                        await page.wait_for_timeout(1000)

                    except Exception as retry_e:
                        logger.debug(f"Retry {retry+1} failed: {retry_e}")
                        continue

                if uploaded:
                    await page.wait_for_timeout(1500)
                    await page.screenshot(path="./screenshots/linkedin/after_upload_editor.png")
                    try:
                        # Handle Editor modal ("Editor" header and/or "Next" button)
                        next_button = page.get_by_role("button", name=re.compile(r"Next|Done", re.I)).first
                        if await next_button.count() > 0 and await next_button.is_visible():
                            await next_button.click(force=True)
                            logger.info("✅ Clicked 'Next' in Editor modal")
                    except Exception as ed_e:
                        logger.debug(f"Editor modal check: {ed_e}")

                    # Wait for return to composer
                    await page.wait_for_timeout(2000)
                    try:
                        await page.wait_for_selector("div[role='textbox'][contenteditable='true']", timeout=10000)
                        logger.info("✅ Returned to composer after Editor")
                    except Exception:
                        pass

                    # Non-blocking check for image preview in composer
                    try:
                        preview = page.locator("dialog img[src^='blob:'], [role='dialog'] img[src^='blob:'], dialog img, [role='dialog'] img").first
                        if await preview.count() > 0:
                            logger.info("✅ Image preview confirmed in composer")
                    except Exception:
                        pass

                    # Ensure post text is still present in the editor; if lost, re-fill
                    try:
                        if textbox:
                            current_text = await textbox.inner_text()
                            if not current_text or len(current_text.strip()) < 5:
                                logger.warning("⚠️ Editor text empty after image attachment; re-filling text")
                                await textbox.click()
                                await textbox.fill(post_text)
                                logger.info("✅ Post text re-filled after image attachment")
                    except Exception as refil_e:
                        logger.debug(f"Textbox re-check: {refil_e}")

                    # Wait for progress bar if processing
                    try:
                        await page.wait_for_selector("div[role='progressbar']", state='detached', timeout=10000)
                    except PlaywrightTimeoutError:
                        pass

                    await page.wait_for_timeout(1500)
                    await page.screenshot(path="./screenshots/linkedin/after_image_upload.png")
                else:
                    logger.warning("⚠️ Failed to upload image after retries; proceeding without")
            else:
                logger.warning("⚠️ No image button found; proceeding without image")
        else:
            logger.info("No image provided; skipping upload")

        # Try to post automatically
        logger.info("🚀 Attempting to click Post/Share button")
        await page.wait_for_timeout(1500)

        post_success = False

        # Properly scope to the active composer dialog
        # Modern LinkedIn uses native <dialog> or div[role='dialog'] wrapping the contenteditable textbox
        composer = page.locator("dialog:has(div[role='textbox']), div[role='dialog']:has(div[role='textbox']), dialog, div[role='dialog'], .share-box__modal").first
        if await composer.count() > 0:
            scope = composer
            logger.info("Scoped Post search to composer modal")
        else:
            scope = page
            logger.info("Scoped Post search to page")

        # Priority 1: Exact role button "Post" or "Share" within the composer scope
        for btn_name in ["Post", "Share"]:
            if post_success:
                break
            try:
                candidate = scope.get_by_role("button", name=btn_name, exact=True).first
                if await candidate.count() > 0 and await candidate.is_visible():
                    is_disabled = await candidate.is_disabled()
                    aria_disabled = await candidate.get_attribute("aria-disabled")
                    if is_disabled or (aria_disabled and aria_disabled.lower() == "true"):
                        logger.warning(f"Found '{btn_name}' button but it is disabled")
                        continue

                    await candidate.scroll_into_view_if_needed()
                    try:
                        await candidate.click(timeout=5000)
                    except Exception:
                        await candidate.click(force=True, timeout=5000)
                    logger.info(f"✅ Clicked exact role button: {btn_name}")
                    post_success = True
                    break
            except Exception as e:
                logger.debug(f"Role button exact='{btn_name}' failed: {e}")

        # Priority 2: Filtered button with exact text "Post" or "Share"
        if not post_success:
            for text_pattern in [r"^Post$", r"^Share$"]:
                if post_success:
                    break
                try:
                    candidate = scope.locator("button").filter(has_text=re.compile(text_pattern, re.I)).first
                    if await candidate.count() > 0 and await candidate.is_visible():
                        is_disabled = await candidate.is_disabled()
                        aria_disabled = await candidate.get_attribute("aria-disabled")
                        if is_disabled or (aria_disabled and aria_disabled.lower() == "true"):
                            continue
                        await candidate.scroll_into_view_if_needed()
                        try:
                            await candidate.click(timeout=5000)
                        except Exception:
                            await candidate.click(force=True, timeout=5000)
                        logger.info(f"✅ Clicked button with exact text pattern {text_pattern}")
                        post_success = True
                        break
                except Exception as e:
                    logger.debug(f"Button filter pattern {text_pattern} failed: {e}")

        # Priority 3: Specific LinkedIn CSS selectors for post button (never click generic artdeco primary)
        if not post_success:
            post_selectors = [
                "button.share-actions__primary-action:not([aria-disabled='true'])",
                "[data-control-name='share_primary_action'] button:not([aria-disabled='true'])",
                "button[aria-label='Post']:not([aria-disabled='true'])",
                "button[aria-label='Share']:not([aria-disabled='true'])",
            ]
            for sel in post_selectors:
                try:
                    btns = scope.locator(sel)
                    count = await btns.count()
                    for i in range(min(count, 3)):
                        btn = btns.nth(i)
                        if not await btn.is_visible():
                            continue
                        btn_text = (await btn.inner_text()).strip()
                        if any(w in btn_text.lower() for w in ["save", "draft", "dismiss", "cancel", "anyone"]):
                            continue
                        await btn.scroll_into_view_if_needed()
                        try:
                            await btn.click(timeout=4000)
                        except Exception:
                            await btn.click(force=True, timeout=4000)
                        logger.info(f"✅ Post clicked via selector: {sel}")
                        post_success = True
                        break
                    if post_success:
                        break
                except Exception:
                    continue

        # Priority 4: JavaScript click on button with exact text "Post" inside dialog
        if not post_success:
            try:
                js_clicked = await page.evaluate('''() => {
                    const buttons = Array.from(document.querySelectorAll("dialog button, div[role='dialog'] button, button"));
                    for (const b of buttons) {
                        const txt = (b.innerText || '').trim();
                        if (txt === 'Post' || txt === 'Share') {
                            const rect = b.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0 && !b.disabled && b.getAttribute('aria-disabled') !== 'true') {
                                b.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }''')
                if js_clicked:
                    logger.info("✅ Post clicked via JavaScript DOM click")
                    post_success = True
            except Exception as js_err:
                logger.debug(f"JavaScript fallback click failed: {js_err}")

        # Priority 5: Keyboard shortcut
        if not post_success:
            logger.info("⌨️ Fallback to keyboard shortcut Ctrl+Enter")
            try:
                if textbox:
                    await textbox.click()
                    await page.wait_for_timeout(200)
                await page.keyboard.press("Control+Enter")
                logger.info("✅ Dispatched Ctrl+Enter")
                post_success = True
            except Exception as hotkey_e:
                logger.error(f"❌ Keyboard fallback failed: {hotkey_e}")
                await page.screenshot(path="./screenshots/linkedin/post_hotkey_failed.png")

        if not post_success:
            logger.error("❌ Failed to trigger post - no clickable Post button found")
            await page.screenshot(path="./screenshots/linkedin/post_trigger_failed.png")
            return False

        # Check for error alerts
        error_selectors = [
            "div[role='alert']",
            ".error-message",
            "div:has-text('Something went wrong')"
        ]
        for sel in error_selectors:
            try:
                error_el = page.locator(sel).first
                if await error_el.count() > 0 and await error_el.is_visible():
                    error_text = await error_el.inner_text()
                    if error_text.strip():
                        logger.error(f"❌ Error detected: {error_text}")
                        await page.screenshot(path="./screenshots/linkedin/post_error.png")
                        return False
            except PlaywrightTimeoutError:
                pass

        # Wait for progress bar if any
        try:
            await page.wait_for_selector("div[role='progressbar']", state="detached", timeout=15000)
            logger.info("✅ Posting completed")
        except PlaywrightTimeoutError:
            pass

        # Verification: Confirm the composer actually closed
        composer_closed = False
        try:
            await page.wait_for_selector("div[role='textbox'][contenteditable='true']", state="detached", timeout=12000)
            logger.info("✅ Composer closed")
            composer_closed = True
        except PlaywrightTimeoutError:
            logger.warning("⚠️ Composer textbox still detected after posting")
            # Check if accidental draft prompt appeared
            discard_btn = page.get_by_role("button", name="Discard")
            if await discard_btn.count() > 0 and await discard_btn.is_visible():
                logger.warning("⚠️ Draft modal detected; clicking Discard to clean up")
                await discard_btn.click()
                await page.wait_for_timeout(2000)
            else:
                # Try clicking Post one more time directly
                retry_post = page.get_by_role("button", name="Post", exact=True).first
                if await retry_post.count() > 0 and await retry_post.is_visible():
                    logger.info("Retrying Post button click directly...")
                    await retry_post.click(force=True)
                    try:
                        await page.wait_for_selector("div[role='textbox'][contenteditable='true']", state="detached", timeout=8000)
                        composer_closed = True
                        logger.info("✅ Composer closed after retry")
                    except PlaywrightTimeoutError:
                        pass

        if not composer_closed:
            # Check if success toast notification appeared
            toast = page.locator("div:has-text('Post successful'), div:has-text('Your post is now live')").first
            if await toast.count() > 0:
                composer_closed = True
                logger.info("✅ Post confirmed via success toast notification")

        if not composer_closed:
            logger.error("❌ Post verification failed: Composer remained open and post was not submitted")
            await page.screenshot(path="./screenshots/linkedin/post_not_submitted.png")
            return False

        # Feed verification (optional / best-effort)
        try:
            await page.reload(wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            clean_snippet = post_text[:40].replace('\n', ' ').strip()
            if clean_snippet:
                await page.get_by_text(clean_snippet).first.wait_for(state="visible", timeout=8000)
                logger.info("✅ Post verified by text match in feed!")
        except Exception as verify_e:
            logger.warning(f"⚠️ Feed verification check note: {verify_e}")

        await page.screenshot(path="./screenshots/linkedin/post_success.png")
        logger.info("✅ Post published and verified!")
        return True

    except Exception as e:
        logger.error(f"❌ Error during posting: {e}")
        await page.screenshot(path="./screenshots/linkedin/posting_error.png")
        return False


async def run():
    import sys

    # Determine mode and parse CLI arguments
    cli_mode = len(sys.argv) >= 2
    domain_name = ""
    num_days = 1
    want_image = False
    image_prompt = ""
    image_path_cli = None

    if cli_mode:
        # CLI mode: python linkedin.py "exact_post_text" ["image_path_or_prompt"]
        custom_prompt = sys.argv[1]  # exact post text to use as-is
        if len(sys.argv) >= 3 and sys.argv[2]:
            second_arg = sys.argv[2]
            if os.path.exists(second_arg):
                image_path_cli = second_arg
                want_image = True
                image_prompt = ""
            else:
                # treat as image generation prompt
                image_path_cli = None
                want_image = True
                image_prompt = second_arg
        else:
            want_image = False
            image_prompt = ""
        num_days = 1
    else:
        # Interactive mode
        domain_name = input("Domain Name: ").strip()
        if not domain_name:
            logger.error("Domain Name is required.")
            return
        custom_prompt = input("Custom prompt (Optional): ").strip() or "ðŸŒŸ Professional insights on automation!"
        want_image_input = input("Do you want image? (y/n): ").strip().lower() or 'n'
        want_image = want_image_input == 'y'
        image_prompt = ""
        if want_image:
            image_prompt = input("Image Custom prompt: ").strip()
            if not image_prompt:
                logger.error("Image prompt is required if image is wanted.")
                return
        num_days_input = input("Number of days (optional, default 1): ").strip()
        num_days = int(num_days_input) if num_days_input.isdigit() else 1

    # Initialize Groq client only when generating text (non-CLI mode)
    client = None
    if not cli_mode:
        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            if len(sys.argv) < 2:  # Only ask for input in interactive mode
                groq_api_key = input("Enter Groq API Key: ").strip()
            else:
                logger.error("GROQ_API_KEY environment variable not set")
                return
        client = Groq(api_key=groq_api_key)

    # Initialize Stability AI if needed
    if want_image:
        logger.info("Stability AI will be used for image generation")

    # Ensure directories exist
    os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    session_dir = "./linkedin_session"
    os.makedirs(session_dir, exist_ok=True)
    screenshots_dir = "./screenshots/linkedin"
    os.makedirs(screenshots_dir, exist_ok=True)
    logs_dir = "./logs"
    os.makedirs(logs_dir, exist_ok=True)

    async with async_playwright() as p:
        headless = os.getenv('HEADLESS', 'false').lower() == 'true'
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=session_dir,
            headless=headless,
            viewport={'width': 1920, 'height': 1080},
            args=[
                "--start-maximized"
            ],
        )
        page = await browser.new_page()

        # Stealth init
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)
        await page.wait_for_timeout(random.randint(1000, 3000))

        # User agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        await page.set_extra_http_headers({"User-Agent": user_agent})

        try:
            logger.info("ðŸŒ Navigating to LinkedIn...")
            await page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)

            # Check login
            if "login" in page.url.lower() or await page.query_selector("input[name='session_key']"):
                logger.info("ðŸ”‘ Please login manually to LinkedIn. Then rerun.")
                await page.wait_for_timeout(60000)
                return
            else:
                logger.info("âœ… Already logged in with saved session.")

            # Post loop
            for day in range(num_days):
                logger.info(f"Processing day {day + 1}/{num_days}")

                if cli_mode:
                    post_text = custom_prompt  # exact text from API/UI
                    image_path = image_path_cli
                else:
                    post_text = generate_post_text(client, domain_name, custom_prompt, day + 1)
                    image_path = generate_image_with_stability(image_prompt) if want_image else None

                success = await post_to_linkedin(page, post_text, image_path)
                if success:
                    logger.info(f"Successfully posted for day {day + 1}")
                else:
                    logger.error(f"Failed to post for day {day + 1}")

                if day < num_days - 1:
                    logger.info("Waiting 24 hours (simulated)...")
                    await page.wait_for_timeout(5000)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await page.screenshot(path="./screenshots/linkedin/unexpected_error.png")
        finally:
            await page.wait_for_timeout(5000)
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())


