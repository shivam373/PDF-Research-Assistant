"""
video_search.py
Finds a relevant YouTube video using yt-dlp's ytsearch feature.
yt-dlp is actively maintained and has no httpx/proxies compatibility issues.
"""


def find_related_video(topic: str) -> dict | None:
    """
    Search YouTube for *topic* and return info about the top result.

    Returns:
        {
            "title":    str,
            "url":      str,
            "channel":  str,
            "duration": str,   # e.g. "12:34"
        }
        or None if nothing found / yt-dlp not installed.
    """
    try:
        import yt_dlp

        query = topic + " explanation tutorial"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,   # don't download, just get metadata
            "default_search": "ytsearch1",  # fetch exactly 1 result
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)

        entries = info.get("entries") or []
        if not entries:
            return None

        v = entries[0]
        duration_secs = v.get("duration") or 0
        mins, secs = divmod(int(duration_secs), 60)
        duration_str = f"{mins}:{secs:02d}" if duration_secs else ""

        return {
            "title":   v.get("title", ""),
            "url":     f"https://www.youtube.com/watch?v={v['id']}",
            "channel": v.get("channel") or v.get("uploader", ""),
            "duration": duration_str,
        }

    except Exception as exc:
        print(f"[video_search] Search failed: {exc}")
        return None
