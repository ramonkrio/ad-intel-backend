from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.async_api import async_playwright
import asyncio
import json
import re
import os

app = FastAPI(title="Ad Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    theme: str
    country: str = "BR"
    limit: int = 20

class Ad(BaseModel):
    id: str
    page_name: str
    body: str
    title: str | None = None
    caption: str | None = None
    snapshot_url: str | None = None
    video_url: str | None = None
    image_url: str | None = None
    start_date: str | None = None


async def scrape_ads(theme: str, country: str = "BR", limit: int = 20) -> list[dict]:
    ads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="pt-BR",
        )

        page = await context.new_page()

        # Block unnecessary resources to speed up
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda r: r.abort())

        url = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={country}&q={theme}&search_type=keyword_unordered"

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)

            # Scroll to load more ads
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 1200)")
                await asyncio.sleep(1.5)

            # Try to extract ad data from the page
            ad_data = await page.evaluate("""
                () => {
                    const ads = [];
                    
                    // Try to find ad containers
                    const containers = document.querySelectorAll('[data-testid="ad-card"], [class*="x8gbvx"], [class*="_7jyr"]');
                    
                    // Fallback: get all divs that look like ad cards
                    const allDivs = document.querySelectorAll('div[role="article"]');
                    const targets = containers.length > 0 ? containers : allDivs;
                    
                    targets.forEach((el, idx) => {
                        if (idx >= 25) return;
                        
                        const text = el.innerText || '';
                        const links = Array.from(el.querySelectorAll('a[href]')).map(a => a.href);
                        const videos = Array.from(el.querySelectorAll('video')).map(v => v.src || v.getAttribute('data-video-id'));
                        const images = Array.from(el.querySelectorAll('img')).map(i => i.src).filter(s => s && !s.includes('emoji'));
                        
                        if (text.length > 30) {
                            ads.push({
                                raw_text: text.slice(0, 2000),
                                links: links.slice(0, 5),
                                videos: videos.filter(Boolean),
                                images: images.slice(0, 3),
                            });
                        }
                    });
                    
                    return ads;
                }
            """)

            # Also try to intercept API responses
            # Parse raw text into structured ads
            for i, raw in enumerate(ad_data[:limit]):
                text = raw.get("raw_text", "")
                lines = [l.strip() for l in text.split("\n") if l.strip()]

                # Extract page name (usually first meaningful line)
                page_name = lines[0] if lines else "Desconhecido"

                # Extract body (skip first line as page name, join rest)
                body_lines = lines[1:] if len(lines) > 1 else lines
                body = " ".join(body_lines[:10])

                # Find snapshot URL
                snapshot_url = next((l for l in raw.get("links", []) if "facebook.com/ads/library" in l), None)

                ads.append({
                    "id": f"scraped_{i}_{hash(body[:50])}",
                    "page_name": page_name[:60],
                    "body": body[:800],
                    "title": None,
                    "caption": None,
                    "snapshot_url": snapshot_url,
                    "video_url": raw.get("videos", [None])[0],
                    "image_url": raw.get("images", [None])[0],
                    "start_date": None,
                })

        except Exception as e:
            await browser.close()
            raise HTTPException(status_code=500, detail=f"Erro no scraping: {str(e)}")

        await browser.close()

    return ads


@app.get("/")
def root():
    return {"status": "ok", "service": "Ad Intelligence API"}


@app.post("/search")
async def search_ads(req: SearchRequest):
    if not req.theme.strip():
        raise HTTPException(status_code=400, detail="Tema não pode ser vazio")

    try:
        ads = await scrape_ads(req.theme, req.country, req.limit)
        return {
            "theme": req.theme,
            "total": len(ads),
            "ads": ads,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "healthy"}
