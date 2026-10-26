"""Evidence collection. No inference or paid services are used here."""
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from .common import digest, file_hash, now, read, status, write

REQUIRES = {"frames", "audio", "transcript", "post_context", "speech_if_present"}


def run(command, folder, name, timeout=300):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        log = {"command": command, "returncode": result.returncode,
               "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        log = {"command": command, "returncode": -1, "stdout": "", "stderr": str(exc)}
    write(folder / (name + ".log.json"), log)
    return log


def normalize(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    data = read(manifest_path)
    if not isinstance(data, dict) or not isinstance(data.get("items"), list) or not data["items"]:
        raise ValueError("Manifest must contain a nonempty items array")
    items, ids = [], set()
    for raw in data["items"]:
        item = dict(raw)
        if bool(item.get("url")) == bool(item.get("file")):
            raise ValueError("Each item needs exactly one url or file")
        for key in ("file", "transcript_file", "post_context_file"):
            if item.get(key):
                item[key] = str((manifest_path.parent / item[key]).resolve())
        if item.get("url"):
            parsed = urlsplit(item["url"])
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("URLs must be HTTP(S), without embedded credentials")
            item.setdefault("platform", parsed.hostname.lower().removeprefix("www."))
        else:
            item.setdefault("platform", "local")
        item.setdefault("content_type", "video")
        item.setdefault("requires", ["frames", "speech_if_present"])
        if not isinstance(item["requires"], list) or not set(item["requires"]) <= REQUIRES:
            raise ValueError("Unknown evidence requirement")
        item.setdefault("id", "item-" + digest(item.get("url") or item["file"])[:16])
        if not isinstance(item["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", item["id"]):
            raise ValueError("IDs must be 1–80 letters, digits, underscores or hyphens")
        if item["id"] in ids:
            raise ValueError("Duplicate item ID: " + item["id"])
        ids.add(item["id"])
        items.append(item)
    return items


def verify_bundle(folder, record):
    for name, expected in record["artifacts"].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file() or file_hash(path) != expected:
            raise ValueError("Missing or modified saved evidence: " + name)


def retrieve(item, folder):
    if "file" in item:
        source = Path(item["file"])
        if not source.is_file():
            return None, {}, status("failed", "Local file does not exist")
        target = folder / ("source" + source.suffix.lower())
        try:
            shutil.copyfile(source, target)
            return target, {}, status("success", adapter="local", path=target.name)
        except OSError as exc:
            return None, {}, status("failed", str(exc), adapter="local")
    executable = shutil.which("yt-dlp")
    if not executable:
        return None, {}, status("failed", "Missing yt-dlp; install it to retrieve supported URLs", adapter="yt-dlp")
    result = run([executable, "--ignore-config", "--no-playlist", "--no-progress", "--no-simulate", "--ignore-errors",
                  "--socket-timeout", "30", "--retries", "1", "--write-info-json", "--write-subs",
                  "--write-auto-subs", "--sub-langs", item.get("subtitle_languages", "all,-live_chat"), "--sub-format", "vtt/best",
                  "--print-to-file", "after_move:%(filepath)s", str(folder / "downloaded-path.txt"),
                  "--output", str(folder / "source.%(ext)s"), "--", item["url"]], folder, "retrieval")
    metadata = {}
    for info in folder.glob("*.info.json"):
        try:
            metadata = read(info)
        except (ValueError, OSError):
            pass
    media = [p for p in folder.glob("source.*") if p.suffix.lower() in
             {".mp4", ".webm", ".mkv", ".mov", ".avi", ".m4v", ".flv", ".ts", ".mp3", ".m4a", ".ogg", ".mpeg", ".mpg", ".3gp", ".aac", ".wav", ".opus", ".ogv"} and p.stat().st_size]
    saved_path = folder / "downloaded-path.txt"
    if saved_path.exists():
        paths = [Path(line).resolve() for line in saved_path.read_text().splitlines() if line.strip()]
        valid = [p for p in paths if p.is_relative_to(folder.resolve()) and p.is_file() and p.stat().st_size]
        if valid:
            media = valid
    reason = (result["stderr"] or "Retrieval failed; see retrieval.log.json")[-3000:]
    if not media:
        return None, metadata, status("partial" if metadata else "failed", reason, adapter="yt-dlp")
    # --ignore-errors lets media download survive subtitle failures; keep them visible.
    complete = result["returncode"] == 0 and "ERROR:" not in result["stderr"]
    return media[0], metadata, status("success" if complete else "partial",
                                    None if complete else reason,
                                    adapter="yt-dlp", path=media[0].name)


def collect_item(item, folder, frame_count):
    folder.mkdir(parents=True)
    record = {"schema_version": 1, "id": item["id"], "item": item, "collected_at": now(),
              "collection_config": {"frame_count": frame_count}, "tool_versions": {}}
    for name in ("ffmpeg", "ffprobe", "yt-dlp"):
        executable = shutil.which(name)
        if executable:
            version = run([executable, "--version" if name == "yt-dlp" else "-version"], folder, name + "-version", 15)
            record["tool_versions"][name] = version["stdout"].splitlines()[:1]
        else:
            record["tool_versions"][name] = None
    media, metadata, record["retrieval"] = retrieve(item, folder)
    record["media_available"] = media is not None
    record["audio"] = status("unavailable", "No retrieved media")
    record["frames"] = status("unavailable", "No retrieved media")
    record["transcript"] = status("unavailable", "No transcript supplied or retrieved; no ASR was run")
    record["post_context"] = status("unavailable", "No post text supplied or retrieved")
    # Preserve provider context without treating title alone as the full post caption.
    context = {key: metadata.get(key) for key in ("title", "description", "uploader", "upload_date", "webpage_url")}
    if context.get("description"):
        write(folder / "post-context.json", context)
        record["post_context"] = status("success", path="post-context.json", provenance="adapter description")
    for key, target in (("transcript_file", "transcript"), ("post_context_file", "post_context")):
        if item.get(key):
            try:
                source = Path(item[key])
                text = source.read_text(encoding="utf-8")
                if not text.strip():
                    raise ValueError("Supplied file is empty")
                destination = target + source.suffix
                (folder / destination).write_text(text, encoding="utf-8")
                record[target] = status("success", path=destination, provenance="user supplied")
            except (OSError, ValueError) as exc:
                record[target] = status("failed", str(exc))
    if not item.get("transcript_file"):
        subtitles = sorted(p.name for p in folder.glob("source.*") if p.suffix in {".vtt", ".srt", ".ttml", ".json3"})
        if subtitles:
            record["transcript"] = status("success", paths=subtitles, provenance="adapter subtitles; may be automatic and unreviewed")
    streams = None
    duration = None
    if media:
        probe = run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media)], folder, "probe")
        try:
            if probe["returncode"] != 0:
                raise ValueError(probe["stderr"])
            info = json.loads(probe["stdout"])
            streams = info["streams"]
            duration = float(info.get("format", {}).get("duration", 0))
        except (ValueError, KeyError, TypeError) as exc:
            record["audio"] = status("failed", "Cannot inspect audio: " + str(exc))
            record["frames"] = status("failed", "Cannot inspect video: " + str(exc))
    if streams is not None:
        audio_present = any(s.get("codec_type") == "audio" for s in streams)
        record["audio_present"] = audio_present
        if audio_present:
            result = run([shutil.which("ffmpeg") or "ffmpeg", "-nostdin", "-v", "error", "-i", str(media), "-vn", "-ac", "1", "-ar", "16000", str(folder / "audio.wav")], folder, "audio")
            record["audio"] = status("success", path="audio.wav") if result["returncode"] == 0 and (folder / "audio.wav").is_file() and (folder / "audio.wav").stat().st_size else status("failed", result["stderr"] or "No audio output")
        else:
            if item.get("url") and record["retrieval"]["status"] != "success":
                record["audio_present"] = None
                record["audio"] = status("unavailable", "Partial retrieval has no audio stream; original audio availability is unknown")
            else:
                record["audio"] = status("absent", "Media has no audio stream")
        if any(s.get("codec_type") == "video" for s in streams) and duration and math.isfinite(duration) and duration > 0:
            frames = []
            for index in range(frame_count):
                timestamp = duration * (index + 0.5) / frame_count
                name = "frame-%03d.jpg" % index
                result = run([shutil.which("ffmpeg") or "ffmpeg", "-nostdin", "-v", "error", "-ss", str(timestamp), "-i", str(media), "-frames:v", "1", "-vf", "scale=1280:1280:force_original_aspect_ratio=decrease", str(folder / name)], folder, "frame-%03d" % index)
                if result["returncode"] == 0 and (folder / name).is_file() and (folder / name).stat().st_size:
                    frames.append({"path": name, "seconds": timestamp})
            record["frames"] = status("success" if len(frames) == frame_count else "partial" if frames else "failed", frames=frames, requested=frame_count, sampling="uniform midpoint samples; not exhaustive")
        else:
            record["frames"] = status("failed", "No video stream or finite positive duration")
    failures = []
    for requirement in item["requires"]:
        if requirement == "speech_if_present":
            ok = record.get("audio_present") is False or record["audio"]["status"] == "success" or record["transcript"]["status"] == "success"
        else:
            ok = record[requirement]["status"] == "success"
        if not ok:
            failures.append(requirement)
    ready = media is not None and not failures
    record["preparation"] = status("success" if ready else "partial" if media is not None else "failed", unmet_requirements=failures)
    record["artifacts"] = {str(p.relative_to(folder)): file_hash(p) for p in sorted(folder.rglob("*")) if p.is_file()}
    write(folder / "evidence.json", record)
    return record


def collect(manifest_path, output, frame_count=8):
    if not 1 <= frame_count <= 100:
        raise ValueError("frame-count must be between 1 and 100")
    items = normalize(manifest_path)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "batch.json").exists():
        previous = read(output / "batch.json")
        if [record["item"] for record in previous["items"]] != items:
            raise ValueError("Output already belongs to a different sample; use a new output directory")
    # Preflight every ID before doing downloads or modifying a batch.
    for item in items:
        folder = output / item["id"]
        if folder.exists():
            if not (folder / "evidence.json").exists():
                raise ValueError("Incomplete existing item directory; use a new output directory: " + item["id"])
            cached = read(folder / "evidence.json")
            if cached["item"] != item or cached["collection_config"] != {"frame_count": frame_count}:
                raise ValueError("ID already has different inputs/settings; use a new output directory: " + item["id"])
            verify_bundle(folder, cached)
    records = []
    for item in items:
        folder = output / item["id"]
        cached = folder / "evidence.json"
        records.append(read(cached) if cached.exists() else collect_item(item, folder, frame_count))
    batch = read(output / "batch.json") if (output / "batch.json").exists() else {"schema_version": 1, "created_at": now(), "items": records}
    if batch["items"] != records:
        raise ValueError("Cached evidence records differ from saved batch")
    if not (output / "batch.json").exists():
        write(output / "batch.json", batch)
    return batch
