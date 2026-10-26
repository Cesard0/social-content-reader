# Social Content Reader

**Inspect a social post before relying on its explanation.** A local Python + Codex workflow that preserves source evidence, distinguishes partial results, and makes missing context explicit.

[Open the walkthrough →](https://cesard0.github.io/social-content-reader/) · [Product decisions](docs/case-study.md#decisions-that-matter) · [Complete public example](docs/public-example.md) · [Run locally](docs/setup.md)

## The task

Explain one post using its speech, visuals, and caption, then answer follow-up questions against the same saved evidence. The intended alternative is manually opening the post, finding speech/text, inspecting visuals, and retaining notes. This task and audience are inferred from the workflow; external user demand and time savings have not been validated.

A title misses the speech. A transcript misses the visuals. A plausible summary can miss both. The project keeps source material, interpretation, and missing pieces distinguishable.

**Documentation walkthrough below; not a shipped application UI.** The historical examples are sanitized records, not an accuracy benchmark.

![Overview of the collection, preservation, and interpretation workflow.](docs/images/workflow.jpg)

## Three choices worth inspecting

| Choice | Why it matters | Inspect |
| --- | --- | --- |
| Separate evidence preparation from interpretation | A successful download does not prove understanding | [Reader boundary](content_eval/reader.py) |
| Preserve usable media after subtitle errors; label it partial | Useful work can continue without hiding the failure | [Failure and recovery](docs/case-study.md#youtube-failure-and-recovery), [regression test](tests/test_reader.py) |
| Separate retrieval, preparation, and understanding measures | Missing evidence must not disappear from the denominator | [Evaluation implementation](content_eval/evaluation.py), [scoring rules](docs/batch-workflow.md#fixed-scoring-rules) |

## Evidence you can inspect

- **[Complete controlled example](docs/public-example.md):** original synthetic videos, supplied text, extracted frames, actual explanatory text, collection results, and a sampling failure. Reproducible without social-platform access. Codex self-review, not a model benchmark.
- **[Instagram historical example](docs/case-study.md#instagram-demonstration):** saved collection and timestamped explanation, published as sanitized summaries. Original media and full output are not included.
- **[YouTube failure and recovery](docs/case-study.md#youtube-failure-and-recovery):** one recorded subtitle-rate-limit failure, an implemented change, and one later successful retry. The simulated regression test checks a separate branch.
- **[Verification](docs/verification.md):** executed checks and explicit limits. [Evidence map](docs/evidence-map.md) distinguishes public artifacts from historical self-report.

## Contribution and status

Personal project by **César Reverón**, developed with **Codex assistance in implementation and portfolio materials**. The repository documents implemented choices and their tradeoffs; it does not establish which ideas originated with César versus Codex. [Contribution boundaries](docs/case-study.md#contribution-and-ai-assistance).

This is a local tool for personal use. No external customer adoption, production deployment, comprehension benchmark, or measured user benefit is established. The [evaluation plan](docs/evaluation-plan.md) defines what would be needed to test value. No broad platform reliability claim is made.

## How it works

| Python prepares | Codex interprets |
| --- | --- |
| Retrieve accessible video and post context | Read speech and post text |
| Extract timestamped frames and subtitles or local transcription | Inspect frames and use host browser tools for missing context |
| Preserve statuses, hashes, and previous attempts | Explain the content and identify uncertainty |

The Python command produces evidence, not a summary. Image/browser tools come from the host. Cloning this repository does not install automatic assistant activation.

## Run locally

Use Python 3.11+ for media setup. The core package has no third-party Python runtime dependencies.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m content_eval.reader --help
python -m unittest discover -s tests -v
```

Live retrieval requires media tools; speech fallback also requires local model weights. [Setup guide](docs/setup.md) · [Batch evaluation](docs/batch-workflow.md) · [Publication boundaries](docs/publication.md).

The hosted walkthrough is static documentation. Collection and interpretation run locally; no hosted analysis service or model API is bundled.
