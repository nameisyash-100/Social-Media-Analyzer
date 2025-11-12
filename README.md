# Social Media Analyzer — Username Finder

A small Streamlit app that checks common social platforms for a given username by probing public profile URLs and extracting basic page metadata.

- Main file: [app.py](app.py)  
- Dependencies: [requirement.txt](requirement.txt)

## Features
- Concurrent checks across multiple platforms.
- Heuristics to detect whether a profile exists (status codes, redirects, page text).
- Extracts profile image and description from page metadata when available.
- Results shown as cards and a table with CSV export.
- Option to open all found profiles in browser tabs.

## Quickstart

1. Create virtual environment and install dependencies:

```sh
python -m venv .venv
.venv\Scripts\activate   # Windows
# or: source .venv/bin/activate   # macOS / Linux
pip install -r requirement.txt
```

2. Run the app with Streamlit:

```sh
streamlit run app.py
```

3. Open the URL displayed by Streamlit in your browser, enter a username, and press "Search".

## Important code references

- Entry / UI: [app.py](app.py)  
- Platform list: [`app.PLATFORMS`](app.py)  
- Dataclass describing platforms: [`app.Platform`](app.py)  
- HTTP fetch helper: [`app.fetch`](app.py)  
- Metadata parser: [`app.parse_profile_meta`](app.py)  
- Per-platform check: [`app.check_username_on_platform`](app.py)  
- Orchestrator for concurrent checks: [`app.run_checks`](app.py)

## Notes & Caveats
- This tool only checks public URLs and inspects publicly available HTML. It does not use any platform APIs or authenticate.
- Respect each platform's terms of service and rate limits. The app uses a simple concurrency limit and a custom User-Agent header but is not a comprehensive rate-limiting solution.
- Some platforms (e.g., those that heavily rely on JavaScript) may return limited HTML via simple GET requests; results may be incomplete.

## Extending
- Add platforms to [`app.PLATFORMS`](app.py) using the `Platform` dataclass.
- Improve heuristics in [`app.check_username_on_platform`](app.py) or metadata extraction in [`app.parse_profile_meta`](app.py).
- Add caching, retry/backoff, or use official APIs where available for more reliable results.

## License
Include your preferred license when uploading to GitHub.
