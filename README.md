# Social Content Reader

A local Python + Codex workflow for explaining social posts from saved source evidence.

![Read the post. Check the evidence. A saved Instagram example and the collection-to-interpretation workflow.](docs/images/workflow.jpg)

**[See a real example →](docs/case-study.md#instagram-demonstration)** · [Run locally](docs/setup.md) · [Browse the code](content_eval/reader.py)

## Why it exists

A title misses the speech. A transcript misses the visuals. A plausible summary can miss both. This project keeps the accessible source material, the explanation, and the missing pieces distinguishable.

**Python gathers and preserves evidence. Codex interprets it.**

| Python prepares | Codex interprets |
| --- | --- |
| Retrieve accessible video and post context | Read speech and post text |
| Extract timestamped frames and subtitles or local transcription | Inspect frames and use host browser tools for missing context |
| Preserve statuses, hashes, and previous attempts | Explain the content and identify uncertainty |

The Python command produces evidence, not a summary. Codex and its image/browser tools come from the host. Cloning this repository does not install automatic assistant activation.

## One post, inspected

An Instagram creator explains developing software with AI. The saved run contains video, post context, a local transcript, and **12 sampled frames plus five additional frame inspections**. Codex's saved explanation uses timestamps and leaves uncertain software names unresolved.

![Instagram evidence and a paraphrase of the saved explanation.](docs/images/instagram-demo.jpg)

[Read the walkthrough](docs/case-study.md#instagram-demonstration) · [Inspect the sanitized record](docs/examples/instagram-demo.json) · [Original post by kem_glitch](https://www.instagram.com/p/DemLMidtxxj/)

## A failure worth showing

A YouTube subtitle request hit **HTTP 429**. The first attempt saved no local video or frames. The collector was changed to preserve usable media while keeping remaining errors labeled partial; the reader narrowed subtitle requests and supports local transcription when needed.

A later live retry saved video, English subtitles, audio, and 12 frames. A separate simulated regression test checks that a subtitle error does not discard usable media or mislabel it complete.

![YouTube subtitle failure, the collector decision, and observed recovery.](docs/images/youtube-recovery.jpg)

[Read the engineering story](docs/case-study.md#youtube-failure-and-recovery) · [Recovery record](docs/examples/youtube-recovery.json) · [Regression tests](tests/test_reader.py)

## Run locally

Use Python 3.11+ for the media setup. The core package has no third-party Python runtime dependencies.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m content_eval.reader --help
python -m unittest discover -s tests -v
```

Live retrieval requires media tools; speech fallback also requires local model weights. **[Follow the setup guide](docs/setup.md)** before running a link. The separate [batch evaluation workflow](docs/batch-workflow.md) supports human-reviewed references and auditable scoring; no model API is bundled.

## Status, contribution, and boundaries

Personal project by César Reverón, developed with Codex assistance. The [verification record](docs/verification.md) documents **20 passing tests**, including real FFmpeg extraction/cache reuse, and a fresh-environment installation check.

These are specific observed examples, not a cross-platform accuracy or reliability benchmark. Platform restrictions, transcription errors, and sparse frame sampling remain limitations. The public package does not include the original local Codex skill installation.

The screenshots are a designed walkthrough of sanitized saved records, not a shipped app UI. Raw media, full transcripts, logs, chats, credentials, and local configuration remain private. [Publication boundaries](docs/publication.md).

The [HTML walkthrough](docs/walkthrough.html) is also included for local viewing: run `python3 -m http.server 8000 --bind 127.0.0.1` from this repository, then open `http://127.0.0.1:8000/docs/walkthrough.html`.
