# A complete public example: what two frames miss

**Original synthetic media · executed collection · Codex-written explanation and self-review · no comprehension score**

The historical social examples omit source media. This example makes the whole chain inspectable without redistributing anyone else's post. It demonstrates collection behavior and a sampling limit. It does not establish user demand, model accuracy, social-platform access, or time savings.

## Input and task

Explain what visibly changes, and state what the available evidence cannot establish.

- [Six-second source: steady change](examples/controlled/steady.mp4)
- [Six-second source: brief extra event](examples/controlled/brief.mp4)
- [Supplied transcript](examples/controlled/transcript.txt): “The indicator changes position halfway through.” This is authored text; the videos have no audio. No ASR is tested.
- [Supplied context](examples/controlled/context.txt): identifies this as a synthetic fixture, not a real product or customer recording.
- Third input: an intentionally missing video file. The failure remains in the sample.

## Prepared evidence

The existing collector extracted midpoint frames at **1.5 and 4.5 seconds** from each available video.

| 1.5 seconds | 4.5 seconds |
| --- | --- |
| ![Red square on the left at 1.5 seconds](examples/controlled/steady-0.jpg) | ![Green square on the right at 4.5 seconds](examples/controlled/steady-1.jpg) |

The brief-event video's sampled frames look the same: [1.5 seconds](examples/controlled/brief-0.jpg), [4.5 seconds](examples/controlled/brief-1.jpg).

## Actual explanatory text

The following is the complete illustrative answer composed by Codex after inspecting the frames and fixture specification. It is not a blinded model run and must not be scored as one.

> At 1.5 seconds, a red square appears on the left. At 4.5 seconds, a green square appears on the right. The supplied text says the indicator changes position halfway through. These samples establish the two observed states; they do not establish every event between them. Colors alone do not prove a real queue status, business outcome, or launch readiness. For the missing video, no visual explanation is supported.

## The event the samples miss

The second video contains a blue banner from **2.8 to just before 3.0 seconds**. Neither uniform midpoint sample captures it. An additional extraction at **2.9 seconds** exposes it:

![Blue banner above the red square at 2.9 seconds](examples/controlled/brief-extra-2.9.jpg)

After inspecting that additional frame, the explanation can add:

> The brief-event source also shows a blue banner at 2.9 seconds. The original two-frame evidence set missed it; the first explanation cannot be treated as a complete account of the source.

## Comparison and observed result

This compares available information, not competing models' performance.

| Evidence available | Supported observation | Still unsupported |
| --- | --- | --- |
| Supplied text only | A position change is described | Colors, positions, brief banner |
| Text + two sampled frames | Red/left and green/right states | Whether a short event occurred between samples |
| Additional 2.9-second frame | Blue banner also appears in the brief-event source | Any real-world product or customer meaning |
| Missing source | Collection failed | Any visual explanation |

[Executed collection record and artifact hashes](examples/controlled/collection.json): **2 of 3 inputs retrieved and prepared; 1 intentionally failed**. Both available videos passed the declared preparation requirements. Those counts describe deliberately constructed local cases, not platform reliability. Cache reuse was also checked. Reported elapsed time measures local collection only, excluding generation and interpretation.

**Product consequence:** preparation success must remain separate from comprehension or completeness. Questions about transient events require targeted inspection or more complete coverage; simply increasing the number of uniform samples cannot guarantee capture. This example supports retaining the boundary, not claiming an accuracy improvement.

## Reproduce

From the repository root with Python 3.11+, FFmpeg, and ffprobe:

```sh
python3 tools/public_example.py /tmp/scr-example-run
```

Use a new directory. The script generates both videos and supplied text, collects through the existing package, retains the missing input, verifies cache reuse, extracts the extra frame, and exports only allowlisted synthetic artifacts. It refreshes the checked-in example assets; inspect the diff before committing. Exact encoded bytes can differ across FFmpeg versions. Full machine-local logs remain in the working directory and are not published.

The fixture, source videos, text, frames, and explanatory answer were all created with Codex assistance. No independent human reviewed the example. The existing evaluation code's human-review requirement is unchanged. See the [next evaluation plan](evaluation-plan.md).
