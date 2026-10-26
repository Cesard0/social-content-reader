# Batch evidence and evaluation

Local Python MVP. Choose the sample yourself: URLs supported by the `yt-dlp` adapter, local video files, or a mixture. No platform allowlist. Support by an adapter does **not** guarantee access: login walls, private/deleted posts, geo restrictions, rate limits, unsupported URLs, and missing tools produce recorded failures or partial results.

No API key or paid model is needed for collection or reference templates. Batch collection does not call a model; the content reader can run a local speech model. Stage 2 imports answers and human or optional automated scores produced separately.

## Run

Python 3.9+. From this directory:

```sh
python3 -m content_eval --help
```

Optional install: `python3 -m pip install -e .` provides the `content-eval` command. The existing media environment is documented in [setup guide](setup.md). Use it with the native tools on PATH:

```sh
export PATH="$PWD/.venv-media/bin:/opt/homebrew/bin:$PATH"
python -m content_eval --help
```

For a fresh machine, install FFmpeg (including `ffprobe`) for audio/frame extraction and a current supported Python with `yt-dlp` for URL retrieval:

```sh
brew install ffmpeg
python3 -m pip install 'yt-dlp[default]'
```

Tool behavior: [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#usage-and-options), [FFmpeg documentation](https://ffmpeg.org/ffmpeg.html). Tool versions and command logs are saved with evidence. User yt-dlp configuration is ignored so the collection settings are explicit. Subtitle failures permit media retrieval to continue and remain visible as partial retrieval. Batch collection requests all subtitles except live chat; the automatic reader requests English and original-language subtitle tags, then falls back to ASR. There is no authentication configuration in this MVP; restricted sources fail explicitly. Supported URLs are individual videos/posts, not playlist batches. Put each selected video in the manifest.

## Stage 1: collect once

Create `manifest.json` (paths relative to the manifest):

```json
{
  "items": [
    {"id": "local-01", "file": "clips/chosen.mp4"},
    {
      "id": "post-01",
      "url": "https://www.youtube.com/watch?v=YOUR_VIDEO_ID",
      "platform": "youtube",
      "content_type": "short_video",
      "requires": ["frames", "transcript", "post_context"]
    }
  ]
}
```

```sh
python3 -m content_eval collect manifest.json --out evidence/my-sample --frame-count 8
```

Use `file` or `url` per item. Optional `transcript_file` and `post_context_file` let you supply saved text; these take precedence over adapter text. [example manifest](../examples/manifest.json) shows every field. Explicit IDs are recommended; otherwise IDs are derived from the exact URL or resolved local path. Reusing an ID with different inputs/settings is rejected. Different URLs for the same post receive different auto IDs; deduplicate your sample before collecting.

`platform` and `content_type` are grouping labels you control. Defaults are URL hostname / `local`, and `video`. Set consistent platform labels across URL variants; hostname alone does not identify a short, story, reel, or livestream.

Each item saves:

- A copy of source media, even for local files.
- Retrieval status and reason, audio-stream detection, extracted mono audio, available subtitle files, sampled frames with timestamps, and available post description or supplied context.
- Separate `success`, `partial`, `failed`, `unavailable`, or `absent` states as applicable. `absent` audio means the inspected file has no audio stream; missing inspection is a failure, never silence.
- Input and processing settings, tool versions, timestamps, command output, and SHA-256 hashes of preserved artifacts.

`batch.json` is the machine-readable evidence inventory. `collection-report.md` is the readable status report. `reference-template.json` contains the seven question categories and default rubric. Evidence/logs may contain personal post content or signed URLs; these are local artifacts.

Default preparation requirements: all requested frame samples, plus audio **or** transcript when an audio stream exists. Silence can satisfy the speech requirement; unknown audio availability cannot, unless a transcript is supplied. Add `transcript`, `post_context`, or `audio` to `requires` for stricter evaluations. The complete choices are `frames`, `audio`, `transcript`, `post_context`, `speech_if_present`. Declare requirements before collecting. Preparation means these checks passed; it does not mean the evidence covers every fact in the video.

Eight uniformly spaced midpoint frames are sparse evidence. Brief actions or text can be missed. Audio does not imply a transcript; the batch collector performs no ASR or OCR (the separate reader can run local ASR). Retrieved subtitles may be automatic and unreviewed. A title alone is not counted as post-context availability. Reference reviewers must inspect full saved media when the question requires more than the prepared samples.

Rerunning the same command verifies cached artifact hashes and reuses the saved batch without downloading, copying original inputs, or processing media again. Original files may subsequently be unavailable. Edited original sources are intentionally not re-imported into the snapshot. Saved failures are also reused. To retry failures, change frame settings, or collect updated content, use a new output directory. Interrupted item directories are detected; use a new directory for recovery. One output directory belongs to one fixed sample.

Exit codes: `0` complete collection; `2` saved collection has incomplete retrieval/preparation; `1` invalid input or workflow error. Exit `2` still produces references and reports. Failures never silently disappear from the sample.

## Stage 2: freeze, answer, score

1. Edit the saved reference template. For every prepared, non-excluded item, fill each `reference_answer` and `evidence_locations`. Mark `answerability` as `answerable` or `unanswerable`; the latter needs a reference explaining what is missing. Review references against saved evidence, then set `reference_review.status` to `human_reviewed`, with `reviewer` and `reviewed_at`. Generated draft references must receive human review. Failed items need no fabricated references. To omit a prepared item from understanding scoring, supply a nonempty `exclude_reason`.
2. Finalize `analysis_prompt`, point values, `pass_threshold`, and `max_unsupported_claims` **before generating answers**. Freeze the spec:

```sh
python3 -m content_eval freeze evidence/my-sample/batch.json evidence/my-sample/reference-template.json --out frozen-spec.json
python3 -m content_eval answer-template frozen-spec.json --out answers.json
```

3. Give your chosen model the exact frozen analysis prompt, each item's question text/IDs, and the same saved evidence. Do not give it the reference answers. Capture answers in `answers.json`. Record provider, model name, exact version if available (otherwise `version_unavailable_reason`), settings, and `generated_at`. Record all model input/settings details needed to repeat your chosen external runner. Explicitly record an unanswered response; blank strings are rejected. The CLI records the declared prompt; it cannot prove what an external model actually received. The reference freeze is a local hash-checked audit record, not a tamper-proof timestamp authority.

```sh
python3 -m content_eval score-template frozen-spec.json answers.json --out scores.json
```

4. Fill every question's `label`, `rationale`, and `evidence_locations`. Audit the **entire** model response for unsupported factual claims, even outside the question being scored. Set `unsupported_claims_reviewed` to `true`. Use an empty `unsupported_claims` list only after review; each finding needs `claim`, `rationale`, and `answer_location`. Record the human scorer's name.

```sh
python3 -m content_eval evaluate frozen-spec.json answers.json scores.json --out evaluation-runs/run-01
```

Outputs: readable `report.md` with question/reference/answer comparisons, and `results.json` with per-item scores, complete frozen references, answers, scorer inputs, hashes, exclusions, and summaries by platform and content type. Reporting never changes the evidence bundle. Existing evaluation artifacts cannot be overwritten; use new paths for revisions.

### Question coverage

Every prepared, non-excluded item must cover all seven categories: topic/message; important facts; events/actions/order; screen-only information; speech-only information; caption/post context; and unsupported/invented details. You can customize question wording and add questions. Questions may be explicitly unanswerable when evidence is absent. This rewards calibrated abstention; it does not demonstrate comprehension of missing content. The separate evidence rates expose those gaps. Select stricter evidence requirements for a benchmark that needs complete modalities.

### Fixed scoring rules

| Label | Points | Rule |
| --- | ---: | --- |
| `correct` | 1 | All material reference facts correct, no material contradictions |
| `partially_correct` | 0.5 | Some material reference facts correct; incomplete or partly wrong |
| `incorrect` | 0 | Wrong, unsupported, or unanswered despite sufficient evidence |
| `appropriately_unanswered` | 1 | Explicit insufficient-evidence answer to a reference marked unanswerable |

Answerable questions cannot earn abstention credit. Unanswerable questions accept only `incorrect` or `appropriately_unanswered`. Equal question weights; per-item score is earned points / question count. Defaults: score at least **80%** and **zero unsupported factual claims** to pass understanding. Threshold and permitted unsupported-claim count can be changed in the draft and then frozen. Point values are deliberately fixed in this MVP. Invented claims are counted and reported separately even when they also reduce a question score.

| Result | Numerator / denominator |
| --- | --- |
| Retrieval success | Fully retrieved items / entire selected sample |
| Evidence preparation success | Fully retrieved items meeting declared requirements / fully retrieved items |
| Evidence preparation across sample | All prepared items, including usable partial retrievals / entire sample |
| Understanding score | Question points earned / possible question points among prepared, non-excluded items |
| Understanding item pass | Items passing frozen understanding rules / prepared, non-excluded items |
| End-to-end pass | Fully retrieved, prepared items passing understanding / entire selected sample |
| Unsupported claim item rate | Evaluated items with any unsupported claims / evaluated items |

Understanding is question-weighted when items have different question counts. Usable partial retrievals can be scored for understanding, but fail end to end. Explicit exclusions affect only understanding denominators: they remain in retrieval and end-to-end denominators. Missing answers/scores for an eligible item are errors, never silent exclusions. Zero denominators produce `null` / N/A. Reports list exclusions with reasons, unprocessed IDs, and every numerator and denominator. Every result applies **only to the tested sample**, never all social media.

### Optional automated judge

Produce the same `scores.json` structure, set `scorer.type` to `automated`, and record `scorer.model` as an object with provider/name/version (or version-unavailable reason), the exact judge `prompt`, and optional `reviewed_by`. Preserve question rationales, evidence references, and claim findings. Scores are labeled automated-assisted and never independent ground truth, even when answer and judge models differ. A model judging itself receives the same explicit non-independent label. Human-reviewed references remain mandatory. No automated judge API is bundled or required.

## Verify

```sh
python3 -m unittest discover -s tests -v
```

Tests exercise mixed retrieval outcomes, preserved bundles and cache integrity, separate metric denominators, human-review gates, abstention rules, unsupported-claim failures, complete answer/score IDs, frozen hashes, and automated-judge labeling. Deterministic tests simulate command results. An additional real FFmpeg integration test runs when FFmpeg and ffprobe are on PATH and otherwise explicitly skips. It generates a synthetic video with audio, saves frames/audio, deletes the original, and verifies cached reuse. This suite does not measure live platform reliability or explanation accuracy. See the case study for individually observed live examples.
