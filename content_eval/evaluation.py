"""Frozen reference sets, externally generated answers, and auditable scoring."""
from pathlib import Path

from .common import digest, file_hash, now, read, write
from .evidence import verify_bundle

QUESTIONS = [
    ("topic", "What is the main topic and intended message?"),
    ("details", "What important facts and details are supported by the evidence?"),
    ("sequence", "What events or actions occur, and in what order?"),
    ("screen_only", "What information is visible only on screen?"),
    ("speech_only", "What information is conveyed only through speech?"),
    ("post_context", "How does the caption or post text change the video's meaning?"),
    ("unsupported", "Which factual claims cannot be supported by the available evidence?"),
]
POINTS = {"correct": 1, "partially_correct": 0.5, "incorrect": 0, "appropriately_unanswered": 1}


def create_template(batch_path, destination):
    batch_path = Path(batch_path).resolve()
    batch = read(batch_path)
    result = {
        "schema_version": 1, "state": "draft", "batch_sha256": file_hash(batch_path),
        "scope": "Results apply only to this selected tested sample.",
        "analysis_prompt": "Using only the supplied evidence, answer each question by ID. Cite frame timestamps, transcript spans, or post text. State when evidence is insufficient. Do not invent facts.",
        "rubric": {"points": POINTS, "pass_threshold": 0.8, "max_unsupported_claims": 0,
                   "rules": {"correct": "All material reference facts correct; no material contradictions.",
                             "partially_correct": "Some material reference facts correct, but incomplete or partly wrong.",
                             "incorrect": "Materially wrong, unsupported, or unanswered despite sufficient evidence.",
                             "appropriately_unanswered": "Explicitly states insufficient evidence for a question marked unanswerable in the reviewed reference."}},
        "items": [],
    }
    for item in batch["items"]:
        result["items"].append({"id": item["id"], "exclude_reason": None,
                                "reference_review": {"status": "pending", "reviewer": "", "reviewed_at": ""},
                                "questions": [{"id": key, "category": key, "question": question,
                                               "answerability": "answerable", "reference_answer": "",
                                               "evidence_locations": []} for key, question in QUESTIONS]})
    save_new(destination, result)
    return result


def save_new(path, value):
    if Path(path).exists():
        raise ValueError("Refusing to overwrite existing artifact: " + str(path))
    write(path, value)


def ready(item):
    return item["media_available"] and item["preparation"]["status"] == "success"


def validate_references(spec, batch):
    rubric = spec["rubric"]
    if rubric["points"] != POINTS:
        raise ValueError("Supported point values are correct=1, partial=0.5, incorrect=0, appropriately unanswered=1")
    threshold = rubric["pass_threshold"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 < threshold <= 1:
        raise ValueError("pass_threshold must be greater than 0 and at most 1")
    maximum = rubric["max_unsupported_claims"]
    if type(maximum) is not int or maximum < 0:
        raise ValueError("max_unsupported_claims must be a nonnegative integer")
    if not spec["analysis_prompt"].strip():
        raise ValueError("A fixed analysis_prompt is required")
    actual = [item["id"] for item in batch["items"]]
    references = [item["id"] for item in spec["items"]]
    if len(set(references)) != len(references) or set(actual) != set(references):
        raise ValueError("Reference IDs must match the entire selected batch; use explicit exclusions")
    by_id = {item["id"]: item for item in batch["items"]}
    for item in spec["items"]:
        if item.get("exclude_reason") is not None:
            if not isinstance(item["exclude_reason"], str) or not item["exclude_reason"].strip():
                raise ValueError("Exclusions require a nonempty reason")
            continue
        if not ready(by_id[item["id"]]):
            continue
        review = item["reference_review"]
        if review["status"] != "human_reviewed" or not review["reviewer"].strip() or not review["reviewed_at"].strip():
            raise ValueError("Human-reviewed reference answers required: " + item["id"])
        questions = item["questions"]
        ids = [q["id"] for q in questions]
        if len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
            raise ValueError("Question IDs must be unique and nonempty")
        if not {key for key, _ in QUESTIONS} <= {q["category"] for q in questions}:
            raise ValueError("Every reference must cover all seven question categories")
        for q in questions:
            if q["answerability"] not in ("answerable", "unanswerable") or not q["reference_answer"].strip() or not q["question"].strip():
                raise ValueError("Complete each reference, including why unanswerable: " + item["id"] + "/" + q["id"])
            if not isinstance(q["evidence_locations"], list) or not q["evidence_locations"]:
                raise ValueError("Reference evidence locations (or missing-evidence explanation) required")


def freeze(batch_path, reference_path, destination):
    batch_path = Path(batch_path).resolve()
    batch, spec = read(batch_path), read(reference_path)
    if spec["state"] != "draft" or spec["batch_sha256"] != file_hash(batch_path):
        raise ValueError("Draft reference template must match this unchanged batch")
    validate_references(spec, batch)
    for item in batch["items"]:
        verify_bundle(batch_path.parent / item["id"], item)
    spec.update(state="frozen", frozen_at=now(), batch=batch)
    spec["spec_sha256"] = digest(spec)
    save_new(destination, spec)
    return spec


def load_spec(path):
    spec = read(path)
    claimed = spec.pop("spec_sha256")
    if claimed != digest(spec) or spec["state"] != "frozen":
        raise ValueError("Frozen spec was modified or is invalid; create a new version")
    spec["spec_sha256"] = claimed
    validate_references(spec, spec["batch"])
    return spec


def answer_template(spec_path, destination):
    spec = load_spec(spec_path)
    batch = {i["id"]: i for i in spec["batch"]["items"]}
    save_new(destination, {"spec_sha256": spec["spec_sha256"], "analysis_prompt_sha256": digest(spec["analysis_prompt"]),
                           "model": {"provider": "", "name": "", "version": None, "version_unavailable_reason": "", "settings": {}},
                           "analysis_prompt_used": spec["analysis_prompt"], "generated_at": "", "items": [
                               {"id": i["id"], "answers": {q["id"]: "" for q in i["questions"]}}
                               for i in spec["items"] if ready(batch[i["id"]]) and not i.get("exclude_reason")]})


def score_template(spec_path, answers_path, destination):
    spec = load_spec(spec_path)
    answers = validate_answers(spec, read(answers_path))
    references = {i["id"]: i for i in spec["items"]}
    save_new(destination, {"spec_sha256": spec["spec_sha256"], "answers_sha256": file_hash(answers_path),
                           "scorer": {"type": "human", "name": "", "model": None,
                                      "prompt": None, "reviewed_by": None},
                           "items": [{"id": item["id"], "questions": {
                               q["id"]: {"label": None, "rationale": "", "evidence_locations": []}
                               for q in references[item["id"]]["questions"]},
                                      "unsupported_claims_reviewed": False, "unsupported_claims": []} for item in answers]})


def validate_answers(spec, answers):
    if answers["spec_sha256"] != spec["spec_sha256"] or answers["analysis_prompt_sha256"] != digest(spec["analysis_prompt"]) or answers["analysis_prompt_used"] != spec["analysis_prompt"]:
        raise ValueError("Answers must record the frozen spec and exact analysis prompt")
    model = answers["model"]
    validate_model(model)
    if not answers["generated_at"].strip():
        raise ValueError("Record answer model/provider and generation time")
    batch = {i["id"]: i for i in spec["batch"]["items"]}
    eligible = {i["id"]: i for i in spec["items"] if ready(batch[i["id"]]) and not i.get("exclude_reason")}
    indexed = index_items(answers["items"], set(eligible), "answers")
    for key, item in indexed.items():
        if set(item["answers"]) != {q["id"] for q in eligible[key]["questions"]}:
            raise ValueError("Answer question IDs must exactly match references")
        if not all(isinstance(a, str) and a.strip() for a in item["answers"].values()):
            raise ValueError("Blank answers are invalid; explicitly record no answer or insufficient evidence")
    return list(indexed.values())


def validate_model(model):
    if not isinstance(model, dict) or not model.get("provider", "").strip() or not model.get("name", "").strip():
        raise ValueError("Record model provider and name")
    if not model.get("version") and not model.get("version_unavailable_reason", "").strip():
        raise ValueError("Record model version or explain why unavailable")


def index_items(items, expected, label):
    indexed = {item["id"]: item for item in items}
    if len(indexed) != len(items) or set(indexed) != expected:
        raise ValueError(label + " IDs must exactly match all eligible items")
    return indexed


def rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator, "rate": numerator / denominator if denominator else None}


def metrics(rows):
    retrieved = [r for r in rows if r["retrieval_success"]]
    processed = [r for r in rows if r["preparation_success"]]
    graded = [r for r in rows if r["evaluated"]]
    return {"retrieval_success": rate(len(retrieved), len(rows)),
            "evidence_preparation_success": rate(sum(r["preparation_success"] for r in retrieved), len(retrieved)),
            "evidence_preparation_across_sample": rate(len(processed), len(rows)),
            "understanding_score": rate(sum(r["points"] for r in graded), sum(r["possible_points"] for r in graded)),
            "understanding_item_pass": rate(sum(r["passed"] for r in graded), len(graded)),
            "end_to_end_pass": rate(sum(r["passed"] for r in graded), len(rows)),
            "unsupported_factual_claims": sum(r["unsupported_claim_count"] for r in graded),
            "unsupported_claim_item_rate": rate(sum(r["unsupported_claim_count"] > 0 for r in graded), len(graded)),
            "excluded_items": [{"id": r["id"], "reason": r["exclusion_reason"]} for r in rows if r["exclusion_reason"]],
            "unprocessed_items": [r["id"] for r in rows if not r["preparation_success"]]}


def evaluate(spec_path, answers_path, scores_path, output):
    spec = load_spec(spec_path)
    answers_doc, scores = read(answers_path), read(scores_path)
    answers = {i["id"]: i for i in validate_answers(spec, answers_doc)}
    if scores["spec_sha256"] != spec["spec_sha256"] or scores["answers_sha256"] != file_hash(answers_path):
        raise ValueError("Scores do not match frozen references and saved answers")
    scorer = scores["scorer"]
    if scorer["type"] not in ("human", "automated") or not scorer["name"].strip():
        raise ValueError("Record scorer type and name")
    if scorer["type"] == "automated" and (not scorer.get("model") or not scorer.get("prompt")):
        raise ValueError("Automated scoring requires judge model/version metadata and exact judge prompt")
    if scorer["type"] == "automated":
        validate_model(scorer["model"])
        if not isinstance(scorer["prompt"], str) or not scorer["prompt"].strip():
            raise ValueError("Record the exact judge prompt")
    # Even a different model is an assistant judge, never independent ground truth.
    label = "human-scored against human-reviewed references" if scorer["type"] == "human" else "automated-assisted scores; not independent ground truth"
    scored = index_items(scores["items"], set(answers), "scores")
    references = {i["id"]: i for i in spec["items"]}
    rows = []
    for evidence in spec["batch"]["items"]:
        key = evidence["id"]
        reference = references[key]
        row = {"id": key, "platform": evidence["item"]["platform"], "content_type": evidence["item"]["content_type"],
               "retrieval_success": evidence["retrieval"]["status"] == "success",
               "retrieval_status": evidence["retrieval"], "preparation_success": ready(evidence),
               "preparation_status": evidence["preparation"], "exclusion_reason": reference.get("exclude_reason"),
               "evaluated": key in scored, "points": 0, "possible_points": 0, "passed": False,
               "unsupported_claim_count": 0, "question_scores": {}, "unsupported_claims": []}
        if key in scored:
            entry = scored[key]
            if entry.get("unsupported_claims_reviewed") is not True:
                raise ValueError("Explicit unsupported-claims audit required: " + key)
            claims = entry["unsupported_claims"]
            if not isinstance(claims, list):
                raise ValueError("unsupported_claims must be an array")
            for claim in claims:
                if not all(isinstance(claim.get(field), str) and claim[field].strip() for field in ("claim", "rationale", "answer_location")):
                    raise ValueError("Each unsupported claim needs claim, rationale, and answer_location")
            if set(entry["questions"]) != {q["id"] for q in reference["questions"]}:
                raise ValueError("Scored question IDs do not match references")
            for question in reference["questions"]:
                score = entry["questions"][question["id"]]
                mark = score["label"]
                if mark not in POINTS or not score["rationale"].strip() or not score["evidence_locations"]:
                    raise ValueError("Every question needs a valid label, rationale, and evidence locations")
                if mark == "appropriately_unanswered" and question["answerability"] != "unanswerable":
                    raise ValueError("Cannot reward abstention on an answerable question")
                if question["answerability"] == "unanswerable" and mark not in ("incorrect", "appropriately_unanswered"):
                    raise ValueError("Unanswerable questions require abstention or an incorrect score")
                row["question_scores"][question["id"]] = {**score, "points": POINTS[mark]}
                row["points"] += POINTS[mark]
                row["possible_points"] += 1
            row["unsupported_claims"] = claims
            row["unsupported_claim_count"] = len(claims)
            # Retrieval partials may be usable for understanding, but do not pass end to end.
            row["understanding_passed"] = row["points"] / row["possible_points"] >= spec["rubric"]["pass_threshold"] and len(claims) <= spec["rubric"]["max_unsupported_claims"]
            row["passed"] = row["understanding_passed"] and row["retrieval_success"]
        rows.append(row)
    # Understanding pass has its own denominator and does not depend on retrieval completeness.
    summary = metrics(rows)
    summary["understanding_item_pass"] = rate(sum(r.get("understanding_passed", False) for r in rows), len(answers))
    groups = {}
    for field in ("platform", "content_type"):
        groups[field] = {}
        for value in sorted({r[field] for r in rows}):
            group_rows = [r for r in rows if r[field] == value]
            group_metrics = metrics(group_rows)
            group_metrics["understanding_item_pass"] = rate(sum(r.get("understanding_passed", False) for r in group_rows), sum(r["evaluated"] for r in group_rows))
            groups[field][value] = group_metrics
    result = {"schema_version": 1, "created_at": now(), "scope": spec["scope"], "score_label": label,
              "spec_sha256": spec["spec_sha256"], "answers_sha256": file_hash(answers_path), "scores_sha256": file_hash(scores_path),
              "model": answers_doc["model"], "scorer": scorer, "rubric": spec["rubric"],
              "summary": summary, "breakdown": groups, "items": rows,
              "audit": {"spec": spec, "answers": answers_doc, "scores": scores}}
    output = Path(output)
    if output.exists():
        raise ValueError("Use a new report output directory")
    output.mkdir(parents=True)
    write(output / "results.json", result)
    (output / "report.md").write_text(render_report(result), encoding="utf-8")
    return result


def render_report(result):
    def formatted(value):
        return ("N/A (0 denominator)" if value["rate"] is None else "%.1f%%" % (value["rate"] * 100)) + " (%s/%s)" % (value["numerator"], value["denominator"])
    lines = ["# Evaluation report", "", result["scope"], "", result["score_label"], "",
             "Model: " + str(result["model"]), "", "Frozen rubric: " + str(result["rubric"]), "",
             "Preparation rate is conditional on full retrieval success. Understanding uses prepared, non-excluded items; abstentions earn credit only for reviewed unanswerable questions. End-to-end includes every sampled item, including failures and exclusions.", ""]
    for heading, summary in [("Whole sample", result["summary"])] + [(field + ": " + value, data) for field, values in result["breakdown"].items() for value, data in values.items()]:
        lines.extend(["## " + heading, "", "| Metric | Result |", "| --- | --- |"])
        for key in ("retrieval_success", "evidence_preparation_success", "evidence_preparation_across_sample", "understanding_score", "understanding_item_pass", "end_to_end_pass", "unsupported_claim_item_rate"):
            lines.append("| " + key.replace("_", " ") + " | " + formatted(summary[key]) + " |")
        lines.extend(["", "Unsupported factual claims: " + str(summary["unsupported_factual_claims"]), "",
                      "Excluded from understanding: " + str(summary["excluded_items"]), "",
                      "Unprocessed: " + str(summary["unprocessed_items"]), ""])
    lines.extend(["## Item audit", ""])
    references = {item["id"]: item for item in result["audit"]["spec"]["items"]}
    answers = {item["id"]: item for item in result["audit"]["answers"]["items"]}
    for row in result["items"]:
        lines.extend(["### " + row["id"], "", "Retrieval: " + str(row["retrieval_status"]), "",
                      "Preparation: " + str(row["preparation_status"]), "",
                      "Points: %s/%s. End-to-end pass: %s. Exclusion: %s" % (row["points"], row["possible_points"], row["passed"], row["exclusion_reason"]), ""])
        for key, score in row["question_scores"].items():
            lines.append("- **%s**: %s — %s. Evidence: %s" % (key, score["label"], score["rationale"], score["evidence_locations"]))
            question = next(q for q in references[row["id"]]["questions"] if q["id"] == key)
            lines.extend(["", "Question: " + question["question"], "", "Reviewed reference: " + question["reference_answer"], "", "Saved answer: " + answers[row["id"]]["answers"][key], ""])
        for claim in row["unsupported_claims"]:
            lines.append("- Unsupported claim: " + str(claim))
        lines.append("")
    lines.extend(["The machine-readable results.json includes the frozen references, exact prompt, saved answers, question scores, judge metadata, and source hashes for audit.", ""])
    return "\n".join(lines)
