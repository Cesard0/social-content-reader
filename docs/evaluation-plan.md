# Value evaluation: defined, not yet completed

**Status: proposed task and protocol. No human-reviewed results, user benefit, or accuracy improvement claimed.**

## User and decision hypothesis

A reader needs to understand one public social post and answer factual follow-ups before relying on it. The current workaround is opening the post, checking available speech/captions/visuals, and keeping notes. This intended task is inferred from the project; demand and frequency have not been validated.

Decision to test: does preserving and reusing multimodal evidence improve supported answers or reduce follow-up effort enough to justify collection/setup cost? A synthetic example establishes inspectability, not this value proposition.

## Bounded comparison

1. Recruit an actual intended user and observe one recurring task and current workaround. If the problem does not recur or matters little, stop rather than optimize irrelevant machinery.
2. Select a small fixed sample before comparing: speech-led, visual-dependent, caption-dependent, brief-event, and inaccessible-source cases. Record selection and exclusions; use media that can be shared lawfully. Report results only for that sample.
3. Use the same questions for the current manual workaround and this workflow. Add a transcript-only condition to isolate whether visual/context evidence changes the answers. Fix the model and prompt where a model is used. Preserve actual inputs and outputs; do not expose reference answers to the answerer.
4. Have a human review references against the full source, including events missed by sampled frames. Freeze the existing reference specification before generating scored answers. The collector's success status is not ground truth.
5. Review factual support, important omissions, unsupported claims, and appropriate abstention. Separately measure setup time, first-answer time, follow-up time, and human correction effort. Preserve failures in the end-to-end denominator.
6. Publish the sample, reviewed references, complete answers, scorer identity/method, exclusions, and per-case results. AI-assisted scoring must keep its non-independent label. No human review may be inferred from an AI pass.

## Decisions the result should change

- Keep or expand the workflow only if it produces a useful improvement on the user's actual task, after setup and correction costs.
- If extra media collection does not improve useful answers or effort, simplify the workflow.
- If sampled frames omit important events, change inspection requirements and rerun the affected cases before making broader claims.
- If access failures dominate, narrow supported use cases or explicitly route to manual inspection.

The relevant magnitude of improvement must be agreed with the actual user before the run; no arbitrary target or completed score is invented here. The [controlled example](public-example.md) is completed collection evidence, not completion of this plan.
