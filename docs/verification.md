# Verification record

Verified October 26, 2026. This is a self-review of the curated public export, not independent product acceptance or a comprehension benchmark.

| Check | Result | Scope |
| --- | --- | --- |
| Existing test suite from source | Passed: 20/20 | Python 3.9.6, with FFmpeg/ffprobe available |
| Fresh virtual environment package install | Passed | Built and installed the wheel on Python 3.13.16 using standard build isolation; no project runtime dependencies |
| Tests against the installed package, outside the source directory | Passed: 20/20 | Python 3.13.16; includes real FFmpeg synthetic-media extraction/cache reuse |
| Both CLI help commands | Passed | `python -m content_eval --help` and `python -m content_eval.reader --help` |
| Installed dependency consistency | Passed | `python -m pip check` |
| Source preservation | Passed | Six package modules, two test modules, and package metadata match the original project byte for byte |
| Evidence selection | Passed | Saved Instagram analysis and YouTube failure/retry records inspected; public summaries use selected fields and paraphrases |
| Desktop visuals | Passed | All three walkthrough views inspected and captured; contrast adjusted for timestamps |
| Mobile layout | Passed | Instagram view checked at 390 CSS pixels; no horizontal overflow |
| Public content review | Passed | Explicit file allowlist; no raw evidence cache, local paths, personal email, chat exports, or credential material in release files |

## Commands

```sh
python -m unittest discover -s tests -v
python -m pip install --no-deps .
python -m content_eval --help
python -m content_eval.reader --help
python -m pip check
```

For the installed-package check, the tests ran from outside the source tree in a new virtual environment. The real FFmpeg test used generated synthetic media, not a social-platform download. Most adapter branches are deterministic simulations.

## What this does not verify

No fresh live Instagram/YouTube download, successful X retrieval, platform-wide reliability, end-user adoption, or general explanation accuracy is claimed. The case-study demonstrations reuse historical saved records. The original host's automatic skill activation is environment-specific and is not installed or re-tested by this public package.

Public examples omit original media and full transcripts, so an external reader cannot independently reproduce every historical observation from repository files alone. Original source posts are linked and may be subject to access restrictions.

## Presentation revision

The README and walkthrough were revised using adapted [gstack design-review guidance](https://github.com/garrytan/gstack/tree/main/design-review) and the owner's preferred Needle comparison as a visual reference. This is a source-guided design pass, not execution of the native gstack runtime. The toolkit, original comparison files, and private design notes are not part of this repository.

The revised presentation uses one clear primary action, warmer colors, stronger type hierarchy, and fewer decorative containers. All three views were checked at 375, 768, and 1440 CSS pixels without horizontal overflow. Navigation targets meet a 44-pixel minimum; the primary action and arrow-key tab navigation were exercised in the browser. Screenshot contents remain sanitized historical summaries. Python source and tests were unchanged by this presentation-only revision.

## Public portfolio follow-up — October 26, 2026

Executed on the public checkout with Python 3.9.6 and FFmpeg/ffprobe 9.0.2:

- Existing suite: **20/20 passed**, including real FFmpeg extraction and saved-source reuse. Both CLI help commands also passed. Core package, tests, and package metadata were unchanged by this revision.
- `python3 tools/public_example.py /tmp/scr-example-run`: exercised here with a fresh temporary directory. Two original synthetic videos were retrieved locally and prepared; an intentionally missing third input remained failed. Recollection verified cache reuse and identical saved records. Nine exported media/text hashes matched their published assets.
- The synthetic frames were visually inspected. The 1.5- and 4.5-second samples miss the brief blue banner; the targeted 2.9-second frame captures it. This checks a designed failure mode, not model comprehension or live-platform reliability. The full illustrative answer was composed with knowledge of the fixture; it is not a blinded comparison.
- New and changed Markdown file targets were checked locally; no missing file targets were found. Public text was checked for local home-directory paths and credential-like prefixes; exported synthetic artifacts were explicitly allowlisted.
- GitHub Pages reported a successful build. Unauthenticated HTTP requests returned **200** for the profile, hosted walkthrough, legacy walkthrough entry, both synthetic videos, collection record, case study, public example, and setup guide.
- Live desktop browser checks confirmed the walkthrough primary action, all three panels, and arrow-key tab navigation. The live page was also rendered inside a 375-CSS-pixel iframe and the main action and tabs exercised. This is a responsive layout check, not physical-device or exhaustive accessibility testing.
- The public profile now shows the professional name, AI/workflow PM focus, profile README, and pinned project. The walkthrough disclaimer is beside the first action; documentation links point to public GitHub files.

All follow-up checks are Codex self-review. No user interviews, measured user benefit, human-reviewed comprehension study, successful X retrieval, or new live Instagram/YouTube retrieval were performed. The existing human-review gate was preserved. The next [value evaluation](evaluation-plan.md) remains a protocol, not a result.
