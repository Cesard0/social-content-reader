import argparse
import json
import sys
from pathlib import Path

from .evidence import collect
from .evaluation import answer_template, create_template, evaluate, freeze, score_template


def main():
    parser = argparse.ArgumentParser(description="Collect reusable evidence and evaluate your selected content sample. No model API required.")
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("collect", help="Save evidence and a draft reference template")
    command.add_argument("manifest")
    command.add_argument("--out", required=True)
    command.add_argument("--frame-count", type=int, default=8)
    command = commands.add_parser("reference-template")
    command.add_argument("batch")
    command.add_argument("--out", required=True)
    command = commands.add_parser("freeze", help="Lock human-reviewed references, sample, analysis prompt, and scoring rules before generating answers")
    command.add_argument("batch")
    command.add_argument("references")
    command.add_argument("--out", required=True)
    command = commands.add_parser("answer-template", help="Create an answer capture file bound to a frozen spec")
    command.add_argument("spec")
    command.add_argument("--out", required=True)
    command = commands.add_parser("score-template", help="Create a scoring worksheet bound to saved answers")
    command.add_argument("spec")
    command.add_argument("answers")
    command.add_argument("--out", required=True)
    command = commands.add_parser("evaluate", help="Validate scores, calculate rates, and save Markdown and JSON reports")
    command.add_argument("spec")
    command.add_argument("answers")
    command.add_argument("scores")
    command.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        if args.command == "collect":
            batch = collect(args.manifest, args.out, args.frame_count)
            output = Path(args.out)
            template = output / "reference-template.json"
            if not template.exists():
                create_template(output / "batch.json", template)
            lines = ["# Evidence collection report", "", "This report describes only the selected sample. No understanding evaluation has been run.", "",
                     "| ID | Platform | Type | Retrieval | Audio | Transcript | Frames | Post context | Preparation |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for item in batch["items"]:
                values = [item["id"], item["item"]["platform"], item["item"]["content_type"]] + [item[key]["status"] for key in ("retrieval", "audio", "transcript", "frames", "post_context", "preparation")]
                lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in values) + " |")
            total = len(batch["items"])
            success = sum(i["retrieval"]["status"] == "success" for i in batch["items"])
            prepared = sum(i["preparation"]["status"] == "success" for i in batch["items"])
            lines.extend(["", "Retrieval success: %s/%s. Evidence prepared across sample: %s/%s." % (success, total, prepared, total), "",
                          "Evidence preparation requires each item's declared requirements. Default: frames and speech evidence when audio is present. Post context and a transcript are tracked separately; add them to requires when essential.", "",
                          "Frames are sparse samples, not a full account of every visual event. Audio availability does not imply a transcript exists.", ""])
            for item in batch["items"]:
                lines.extend(["## " + item["id"], "", "```json", json.dumps({key: item[key] for key in ("retrieval", "audio", "transcript", "frames", "post_context", "preparation")}, indent=2), "```", ""])
            (output / "collection-report.md").write_text("\n".join(lines), encoding="utf-8")
            print("Saved %s items; %s retrieved; %s prepared. See %s" % (total, success, prepared, output / "collection-report.md"))
            return 0 if success == total and prepared == total else 2
        if args.command == "reference-template":
            create_template(args.batch, args.out)
        elif args.command == "freeze":
            freeze(args.batch, args.references, args.out)
        elif args.command == "answer-template":
            answer_template(args.spec, args.out)
        elif args.command == "score-template":
            score_template(args.spec, args.answers, args.out)
        elif args.command == "evaluate":
            result = evaluate(args.spec, args.answers, args.scores, args.out)
            print(json.dumps(result["summary"], indent=2))
        print("Saved " + args.out)
        return 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        print("Error: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
