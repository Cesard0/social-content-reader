"""Single-link preparation for Codex; preserves the batch collector's evidence."""
import argparse
import json
import os
import re
import shutil
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .common import digest, file_hash, now, read, write
from .evidence import collect, run, verify_bundle

ROOT = Path(__file__).resolve().parents[1]


def identify(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    parts = parsed.path.strip("/").split("/")
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        raise ValueError("Expected an HTTP(S) content URL without credentials")
    if host in {"youtube.com", "youtu.be", "music.youtube.com"}:
        key = parts[0] if host == "youtu.be" else (parts[1] if parts[0] in {"shorts", "live", "embed"} and len(parts) > 1 else parse_qs(parsed.query).get("v", [None])[0])
        if not key or not re.fullmatch(r"[A-Za-z0-9_-]{11}", key):
            raise ValueError("Expected an individual YouTube video URL")
        return "youtube", "short" if parts[0] == "shorts" else "video", "https://www.youtube.com/watch?v=" + key
    if host == "instagram.com":
        if len(parts) > 1 and parts[0] in {"p", "reel", "reels", "tv"} and re.fullmatch(r"[A-Za-z0-9_-]+", parts[1]):
            return "instagram", "reel" if parts[0] in {"reel", "reels"} else "post", "https://www.instagram.com/p/" + parts[1] + "/"
        # Stories/share links need browser resolution before collection.
        return "instagram", "story_or_unresolved", url
    if host in {"x.com", "twitter.com", "mobile.twitter.com"}:
        match = re.search(r"/(?:status|statuses)/(\d+)", parsed.path)
        if match:
            return "x", "post", "https://x.com/i/status/" + match[1]
        raise ValueError("Expected an individual X post URL")
    raise ValueError("Expected a YouTube, Instagram, or X content URL")


def instagram(url, folder):
    """Use the already-installed adapter, including all carousel members."""
    import instaloader
    loader = instaloader.Instaloader(dirname_pattern=str(folder), filename_pattern="{shortcode}",
                                    download_comments=False, download_geotags=False,
                                    max_connection_attempts=1, request_timeout=30,
                                    quiet=True)
    post = instaloader.Post.from_shortcode(loader.context, url.rstrip("/").split("/")[-1])
    kind = "carousel" if post.typename == "GraphSidecar" else "video" if post.is_video else "image"
    write(folder / "post-context.json", {"url": url, "text": post.caption, "author": post.owner_username,
                                         "date": post.date_utc.isoformat(), "content_type": kind})
    loader.download_post(post, target="post")
    return kind


def transcribe(record, folder, model):
    if record["transcript"]["status"] == "success":
        return {"status": "subtitles", "folder": str(folder), "evidence": record["transcript"]}
    if record["audio"]["status"] != "success":
        return {"status": "unavailable", "reason": record["audio"].get("reason", "No extracted audio")}
    if not model.is_file() or not shutil.which("whisper-cli"):
        return {"status": "unavailable", "reason": "Missing whisper-cli or model: " + str(model)}
    result = run([shutil.which("whisper-cli"), "-m", str(model), "-f", str(folder / record["audio"]["path"]),
                  "-l", "auto", "-ng", "-ovtt", "-otxt", "-of", str(folder / "speech")], folder, "transcription", 1800)
    vtt = folder / "speech.vtt"
    return {"status": "success" if result["returncode"] == 0 and vtt.is_file() and vtt.stat().st_size else "failed",
            "path": str(vtt), "model": str(model), "provenance": "local whisper.cpp ASR; unreviewed",
            "reason": result["stderr"][-1500:] if result["returncode"] else None}


def prepare(url, cache, model, refresh=False):
    platform, kind, canonical = identify(url)
    base = Path(cache).resolve() / (platform + "-" + digest(canonical)[:16])
    folder = base
    latest = base / "latest.json"
    if latest.exists() and not refresh:
        folder = (base / read(latest)["folder"]).resolve()
        if not folder.is_relative_to(base):
            raise ValueError("Invalid cache pointer")
    if refresh:
        folder = base / ("retry-" + now().replace(":", "-") + "-" + os.urandom(3).hex())
    folder.mkdir(parents=True, exist_ok=True)
    index = folder / "reader.json"
    if index.exists():
        saved = read(index)
        verify_bundle(folder, saved)
        return saved, index
    result = {"url": url, "canonical_url": canonical, "platform": platform,
              "content_type": kind, "collected_at": now(), "videos": [], "images": [], "gaps": []}
    sources = []
    if platform == "instagram" and kind != "story_or_unresolved":
        try:
            result["content_type"] = instagram(canonical, folder)
        except Exception as exc:
            # Adapter failures must still allow browser/yt-dlp fallback.
            result["gaps"].append("Instaloader: " + str(exc))
        result["images"] = [str(p) for p in sorted(folder.glob("*.jpg"))]
        sources = [{"id": "video-%03d" % i, "file": str(p), "post_context_file": str(folder / "post-context.json")}
                   for i, p in enumerate(sorted(folder.glob("*.mp4")))]
    if not sources and not result["images"]:
        sources = [{"id": "video", "url": canonical}]
    if sources:
        manifest = folder / "manifest.json"
        write(manifest, {"items": [dict(s, platform=platform, content_type=kind,
                                       subtitle_languages="en,.*-orig") for s in sources]})
        batch = collect(manifest, folder / "collection", frame_count=12)
        for record in batch["items"]:
            media_folder = folder / "collection" / record["id"]
            result["videos"].append({"evidence": str(media_folder / "evidence.json"),
                                     "retrieval": record["retrieval"],
                                     "speech": transcribe(record, media_folder, model)})
    context = folder / "post-context.json"
    if context.exists():
        result["post_context"] = str(context)
    result["next_step"] = "Codex must read speech/post text, visually inspect timestamped frames/images, and use browser for missing post context/media. This index is not an analysis."
    result["artifacts"] = {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}
    write(index, result)
    if refresh:
        write(latest, {"folder": str(folder.relative_to(base))})
    return result, index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+")
    parser.add_argument("--cache", default=str(ROOT / "evidence" / "reader"))
    parser.add_argument("--model", default=str(ROOT / "evidence" / "models" / "ggml-base.bin"))
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    failed = False
    for url in args.urls:
        try:
            result, path = prepare(url, args.cache, Path(args.model).resolve(), args.refresh)
            print(json.dumps({"url": url, "index": str(path), "platform": result["platform"],
                              "content_type": result["content_type"], "images": len(result["images"]),
                              "videos": [{"retrieval": v["retrieval"]["status"], "speech": v["speech"]["status"]}
                                         for v in result["videos"]], "gaps": result["gaps"]}, ensure_ascii=False))
        except (ValueError, OSError, KeyError) as exc:
            failed = True
            print(json.dumps({"url": url, "error": str(exc)}))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
