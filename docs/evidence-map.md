# Evidence map

The public records are allowlisted summaries of private saved artifacts. Original bytes and their SHA-256 digests are retained locally. Raw artifacts, private hashes, and exact collection times are not distributed. These summaries document the observed examples; they are not independently verified ground truth.

| Public claim | Supporting material | Evidence type |
| --- | --- | --- |
| Instagram video retrieval and local speech transcription succeeded | Selected reader and collection status fields in [Instagram summary](examples/instagram-demo.json) | Historical local artifact inspection |
| 12 sampled frames plus five additional frames were inspected | Recorded timestamp list and completed analysis | Historical Codex inspection notes; not an independent accuracy score |
| Instagram explanation uses timestamps and omits uncertain names | Completed saved analysis, paraphrased in [case study](case-study.md) | Historical agent analysis |
| YouTube subtitle rate limit blocked the first local video collection | First attempt and saved fallback notes, summarized in [recovery record](examples/youtube-recovery.json) | Historical live failure |
| Later retry saved video, audio, subtitles, and 12 frames | Retry collection record and inspection note | Historical live retry |
| Fresh chat reused evidence and inspected 12 frames | Private activation verification record | Historical recorded host verification |
| Usable media survives subtitle errors without being marked complete | [Reader regression test](../tests/test_reader.py) | Simulated downloader branch, verified with the test suite |
| Core tests and real FFmpeg integration pass | [Verification record](verification.md) | Current local execution on the public export |

No full transcripts, original frames, chat exports, or raw diagnostics are required to read the public case study. Original posts remain linked for attribution; a reviewer may encounter platform access restrictions.
