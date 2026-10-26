# Local setup

Use Python 3.11+ for media collection. Core code uses the standard library; media tools are installed separately. The portfolio was checked on macOS; other platforms are not verified here.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m content_eval --help
python -m content_eval.reader --help
```

## Media tools

On macOS with Homebrew:

```sh
brew install ffmpeg whisper.cpp deno
python -m pip install 'yt-dlp[default]' instaloader
```

These commands install available registry versions, not the exact environment of the historical demonstrations. Platform access and upstream changes can affect results. Sources: [yt-dlp](https://github.com/yt-dlp/yt-dlp), [Instaloader](https://instaloader.github.io/), [FFmpeg](https://ffmpeg.org/), [whisper.cpp](https://github.com/ggml-org/whisper.cpp), [Deno](https://deno.com/).

Install the model weights separately by following whisper.cpp's upstream instructions. Put the chosen model at `evidence/models/ggml-base.bin`, or pass its location explicitly:

```sh
python -m content_eval.reader 'https://www.instagram.com/p/DemLMidtxxj/' --model /path/to/ggml-base.bin
```

The reader does not download weights automatically. Without usable subtitles, missing speech tools or weights produce an explicit unavailable status. No paid transcription service is substituted.

## Read the result

The command prints a path to `reader.json`. Open that index and the linked evidence records. Check each video's retrieval and speech fields and the collection record's audio, transcript, frame, and preparation statuses. An empty `gaps` array alone is insufficient.

Read the saved transcript and caption, inspect the sampled frames, and use your host's browser tools for missing context where permitted. Explain only what you could inspect. The Python package has no model client, OCR, or semantic visual analysis.

The original local Codex skill provides that orchestration in the author's environment. It is intentionally excluded here because it contains environment-specific installation details. Cloning this repository does not activate automatic URL reading in your assistant.

## Cache behavior

```sh
python -m content_eval.reader 'https://www.instagram.com/p/DemLMidtxxj/' --refresh
```

Normal reruns verify and reuse cached artifacts, including failures. `--refresh` preserves the earlier attempt and selects a new attempt. Cache paths and logs can contain sensitive or third-party content: keep `evidence/` local.

## Tests and optional evaluation

```sh
python -m unittest discover -s tests -v
```

The FFmpeg integration test skips when FFmpeg/ffprobe are unavailable. Most retrieval tests use controlled adapters and make no live platform requests. See [batch workflow](batch-workflow.md) for evaluation with human-reviewed references; automatic scores are not independent ground truth.
