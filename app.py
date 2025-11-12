# app.py
import asyncio
import re
from dataclasses import dataclass
from typing import Optional, List, Dict
import pandas as pd
import streamlit as st
import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

st.set_page_config(page_title="Username Finder — Social Media Analyzer", layout="wide")

# ---------------------------
# Platform definitions
# ---------------------------

@dataclass
class Platform:
    key: str
    name: str
    url_template: str  # format: use {username}
    example: Optional[str] = None

PLATFORMS: List[Platform] = [
    Platform("twitter", "Twitter / X", "https://twitter.com/{username}"),
    Platform("instagram", "Instagram", "https://www.instagram.com/{username}/"),
    Platform("github", "GitHub", "https://github.com/{username}"),
    Platform("linkedin", "LinkedIn (public)", "https://www.linkedin.com/in/{username}"),
    Platform("facebook", "Facebook", "https://www.facebook.com/{username}"),
    Platform("reddit", "Reddit", "https://www.reddit.com/user/{username}"),
    Platform("youtube", "YouTube (channel)", "https://www.youtube.com/{username}"),
    Platform("medium", "Medium", "https://medium.com/@{username}"),
    Platform("pinterest", "Pinterest", "https://www.pinterest.com/{username}/"),
    Platform("tiktok", "TikTok (web profile)", "https://www.tiktok.com/@{username}"),
    Platform("stack_overflow", "StackOverflow", "https://stackoverflow.com/users/{username}"),
    Platform("snapchat", "Snapchat (public)", "https://www.snapchat.com/add/{username}"),
    # Add more if you want
]

# ---------------------------
# Helpers: fetch & parse
# ---------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Username-Finder/1.0; +https://example.com)"
}

async def fetch(session: aiohttp.ClientSession, url: str, timeout=10) -> Dict:
    """Fetch a URL and return dict with status, text (if any), and final_url."""
    try:
        async with session.get(url, timeout=ClientTimeout(total=timeout), allow_redirects=True) as resp:
            text = await resp.text(errors='ignore')
            return {"status": resp.status, "text": text, "final_url": str(resp.url)}
    except asyncio.TimeoutError:
        return {"status": None, "text": None, "final_url": url}
    except aiohttp.ClientError:
        return {"status": None, "text": None, "final_url": url}
    except Exception:
        return {"status": None, "text": None, "final_url": url}

def parse_profile_meta(html: str) -> Dict:
    """Try to extract og:image and meta description or twitter:description."""
    result = {"image": None, "description": None}
    if not html:
        return result
    soup = BeautifulSoup(html, "html.parser")
    # og:image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        result["image"] = og_image["content"]
    # twitter:image
    if not result["image"]:
        tw_image = soup.find("meta", attrs={"name": "twitter:image"})
        if tw_image and tw_image.get("content"):
            result["image"] = tw_image["content"]
    # description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        result["description"] = desc["content"].strip()
    elif soup.find("meta", property="og:description"):
        result["description"] = soup.find("meta", property="og:description")["content"].strip()
    elif soup.find("meta", attrs={"name": "twitter:description"}):
        result["description"] = soup.find("meta", attrs={"name": "twitter:description"})["content"].strip()
    # fallback: use first <title>
    if not result["description"]:
        title = soup.find("title")
        if title and title.text:
            result["description"] = title.text.strip()
    # trim description length
    if result["description"] and len(result["description"]) > 300:
        result["description"] = result["description"][:297] + "..."
    return result

async def check_username_on_platform(session: aiohttp.ClientSession, platform: Platform, username: str, semaphore: asyncio.Semaphore) -> Dict:
    """Return result dict for a single platform."""
    # some usernames might need URL-encoding (e.g. spaces, special chars)
    encoded = quote_plus(username)
    url = platform.url_template.format(username=encoded)
    async with semaphore:
        r = await fetch(session, url)
    status = r["status"]
    found = False
    image = None
    description = None

    # heuristics to decide if profile exists:
    # - 200 => likely exists
    # - 301/302 that lead to a different page might indicate existence (but not always)
    # - 404 or explicit "Not found" indicates missing
    if status == 200:
        found = True
        meta = parse_profile_meta(r["text"])
        image = meta.get("image")
        description = meta.get("description")
    elif status in (301, 302):
        # follow redirects: if final_url still matches or is not a generic "signup" page, mark found
        final = r.get("final_url", url)
        if final and final != url and "signup" not in final.lower() and "login" not in final.lower():
            found = True
    else:
        # Some platforms return 200 even for missing pages, so add text checks:
        text = (r.get("text") or "").lower()
        if "page not found" in text or "user not found" in text or "sorry, that page doesn't exist" in text:
            found = False
        else:
            # If we have a page text and it contains the username in human-readable areas, mark found
            if username.lower() in text:
                found = True

    return {
        "platform": platform.name,
        "key": platform.key,
        "url": url,
        "status_code": status,
        "found": found,
        "image": image,
        "description": description
    }

async def run_checks(username: str, platforms: List[Platform], concurrency: int = 10, timeout: int = 10) -> List[Dict]:
    """Run checks for all platforms concurrently."""
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit_per_host=concurrency, ssl=False)
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        tasks = [
            check_username_on_platform(session, p, username, semaphore)
            for p in platforms
        ]
        results = await asyncio.gather(*tasks)
    return results

# ---------------------------
# Streamlit UI
# ---------------------------

st.title(" Username Finder — Social Media Analyzer")
st.write("Type a username and the tool will attempt to find matching public profiles across common social platforms.")

with st.form("find_form"):
    col1, col2 = st.columns([3,1])
    with col1:
        username = st.text_input("Enter username (no @ needed)", placeholder="e.g. yashsharma", value="", help="Type the raw username you want to search for.")
    with col2:
        st_write_button = st.form_submit_button("Search")
    st.caption("This tool checks public profile URLs and uses page metadata when available. Respect platform terms of service.")

if st_write_button and username.strip():
    username = username.strip()
    st.info(f"Searching for username: **{username}** across {len(PLATFORMS)} platforms...")
    # run async checks
    try:
        results = asyncio.run(run_checks(username, PLATFORMS, concurrency=12, timeout=12))
    except RuntimeError:
        # In some environments nested event loops cause RuntimeError; fall back to alternative loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_checks(username, PLATFORMS, concurrency=12, timeout=12))

    df = pd.DataFrame(results)
    # reorder columns
    df = df[["platform", "key", "found", "status_code", "url", "image", "description"]]

    # Summary
    found_count = int(df['found'].sum())
    st.success(f"Done — found {found_count} profile(s).")
    st.write("---")
    # Display results in cards/grid
    cols = st.columns(3)
    for i, row in df.iterrows():
        col = cols[i % 3]
        with col:
            status = "✅ Found" if row["found"] else "❌ Not found"
            st.markdown(f"### {row['platform']}  <small style='color:gray'>({status})</small>", unsafe_allow_html=True)
            st.write(f"**URL:** [{row['url']}]({row['url']})")
            if row["status_code"] is not None:
                st.write(f"Status: {row['status_code']}")
            if row["image"]:
                st.image(row["image"], width=160)
            if row["description"]:
                st.write(row["description"])
            st.write("---")

    # Table view & CSV export
    st.subheader("Table view")
    display_df = df.copy()
    display_df["found"] = display_df["found"].map({True: "Found", False: "Not found"})
    st.dataframe(display_df, use_container_width=True)

    csv = df.to_csv(index=False)
    st.download_button("Download CSV", data=csv, file_name=f"{username}_profiles.csv", mime="text/csv")

    # Option: open all found links (client side)
    if found_count > 0:
        if st.button("Open all found profiles (will open in new tabs)"):
            # Build JS to open links in new tabs
            links = df[df["found"]]["url"].tolist()
            js = ""
            for l in links:
                js += f"window.open('{l}', '_blank');"
            st.components.v1.html(f"<script>{js}</script>")

else:
    st.info("Enter a username and press Search to begin.")
