import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from content_eval.common import digest, file_hash, read, status, write
from content_eval.evidence import collect, normalize
from content_eval.evaluation import (answer_template, create_template, evaluate, freeze,
                                     load_spec, score_template)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def path(self, name):
        return self.root / name

    def build_scored_fixture(self):
        records = []
        # Mixed sample: pass, score fail, retrieval failure, explicit exclusion,
        # and usable partial retrieval. All must stay in end-to-end denominator.
        for key, platform, prepared, retrieval in [
            ("pass", "alpha", True, "success"), ("claim", "alpha", True, "success"),
            ("blocked", "beta", False, "failed"), ("exclude", "beta", True, "success"),
            ("partial", "beta", True, "partial")]:
            folder = self.path(key)
            folder.mkdir()
            records.append({"id": key, "item": {"id": key, "platform": platform, "content_type": "video"},
                            "media_available": prepared, "retrieval": status(retrieval),
                            "preparation": status("success" if prepared else "failed"), "artifacts": {}})
        write(self.path("batch.json"), {"items": records})
        create_template(self.path("batch.json"), self.path("references.json"))
        refs = read(self.path("references.json"))
        for item in refs["items"]:
            if item["id"] == "exclude":
                item["exclude_reason"] = "Reviewer chose not to score this item"
                continue
            item["reference_review"] = {"status": "human_reviewed", "reviewer": "Human Reviewer", "reviewed_at": "2026-10-21T18:00:00-04:00"}
            for question in item["questions"]:
                question["reference_answer"] = "Reviewed reference"
                question["evidence_locations"] = ["frame-000.jpg at 1.0 seconds"]
                if question["id"] == "speech_only":
                    question["answerability"] = "unanswerable"
                    question["reference_answer"] = "No audio; cannot establish speech-only content"
        write(self.path("references.json"), refs)
        freeze(self.path("batch.json"), self.path("references.json"), self.path("spec.json"))
        answer_template(self.path("spec.json"), self.path("answers.json"))
        answers = read(self.path("answers.json"))
        answers["model"] = {"provider": "manual test", "name": "fixture-model", "version": "v1", "settings": {}}
        answers["generated_at"] = "2026-10-21T18:05:00-04:00"
        for item in answers["items"]:
            item["answers"] = {key: "No speech evidence" if key == "speech_only" else "Saved model answer" for key in item["answers"]}
        write(self.path("answers.json"), answers)
        score_template(self.path("spec.json"), self.path("answers.json"), self.path("scores.json"))
        scores = read(self.path("scores.json"))
        scores["scorer"]["name"] = "Human Scorer"
        for item in scores["items"]:
            item["unsupported_claims_reviewed"] = True
            for key, score in item["questions"].items():
                score.update(label="appropriately_unanswered" if key == "speech_only" else "correct",
                             rationale="Matches reviewed reference", evidence_locations=["frame-000.jpg"])
            if item["id"] == "claim":
                item["questions"]["details"]["label"] = "partially_correct"
                item["unsupported_claims"] = [{"claim": "Invented fact", "rationale": "Absent from evidence", "answer_location": "details"}]
        write(self.path("scores.json"), scores)

    def score(self):
        return evaluate(self.path("spec.json"), self.path("answers.json"), self.path("scores.json"), self.path("report"))

    def test_full_evaluation_denominators_and_hallucination_gate(self):
        self.build_scored_fixture()
        result = self.score()
        summary = result["summary"]
        self.assertEqual(summary["retrieval_success"], {"numerator": 3, "denominator": 5, "rate": 0.6})
        self.assertEqual(summary["evidence_preparation_success"]["denominator"], 3)
        self.assertEqual(summary["understanding_score"]["numerator"], 20.5)
        self.assertEqual(summary["understanding_score"]["denominator"], 21)
        self.assertEqual(summary["understanding_item_pass"]["numerator"], 2)
        self.assertEqual(summary["end_to_end_pass"]["numerator"], 1)
        self.assertEqual(summary["end_to_end_pass"]["denominator"], 5)
        self.assertEqual(summary["unsupported_factual_claims"], 1)
        self.assertEqual(summary["unprocessed_items"], ["blocked"])
        self.assertEqual(summary["excluded_items"][0]["id"], "exclude")
        self.assertEqual(result["breakdown"]["platform"]["beta"]["understanding_item_pass"]["rate"], 1)
        self.assertIn("tested sample", self.path("report/report.md").read_text())
        self.assertEqual(read(self.path("report/results.json"))["audit"]["answers"]["model"]["version"], "v1")

    def test_frozen_spec_and_answer_hash_are_checked(self):
        self.build_scored_fixture()
        spec = read(self.path("spec.json"))
        spec["rubric"]["pass_threshold"] = 0.1
        write(self.path("tampered.json"), spec)
        with self.assertRaisesRegex(ValueError, "modified"):
            load_spec(self.path("tampered.json"))
        answers = read(self.path("answers.json"))
        answers["items"][0]["answers"]["topic"] = "Changed after scoring"
        write(self.path("answers.json"), answers)
        with self.assertRaisesRegex(ValueError, "Scores do not match"):
            self.score()

    def test_no_credit_for_abstention_on_answerable_question(self):
        self.build_scored_fixture()
        scores = read(self.path("scores.json"))
        scores["items"][0]["questions"]["topic"]["label"] = "appropriately_unanswered"
        write(self.path("scores.json"), scores)
        with self.assertRaisesRegex(ValueError, "Cannot reward abstention"):
            self.score()

    def test_references_must_be_human_reviewed(self):
        self.build_scored_fixture()
        refs = read(self.path("references.json"))
        refs["items"][0]["reference_review"]["status"] = "model_generated"
        write(self.path("references.json"), refs)
        with self.assertRaisesRegex(ValueError, "Human-reviewed"):
            freeze(self.path("batch.json"), self.path("references.json"), self.path("new-spec.json"))

    def test_automated_judge_is_labeled_and_auditable_even_same_model(self):
        self.build_scored_fixture()
        scores = read(self.path("scores.json"))
        scores["scorer"].update(type="automated", model={"provider": "manual test", "name": "fixture-model", "version": "v1"}, prompt="Judge using the frozen rubric")
        write(self.path("scores.json"), scores)
        result = self.score()
        self.assertIn("not independent ground truth", result["score_label"])
        self.assertIn("Judge using", result["audit"]["scores"]["scorer"]["prompt"])

    def test_missing_duplicate_and_extra_scores_rejected(self):
        self.build_scored_fixture()
        original = read(self.path("scores.json"))
        for mutate in (lambda x: x["items"].pop(), lambda x: x["items"].append(copy.deepcopy(x["items"][0]))):
            scores = copy.deepcopy(original)
            mutate(scores)
            write(self.path("scores.json"), scores)
            with self.assertRaisesRegex(ValueError, "IDs must exactly match"):
                self.score()

    def test_local_collection_preservation_and_no_reprocessing(self):
        self.path("clip.mp4").write_bytes(b"fixture video bytes")
        self.path("speech.txt").write_text("Reviewed speech")
        self.path("caption.txt").write_text("Caption changes the meaning")
        write(self.path("manifest.json"), {"items": [{"file": "clip.mp4", "transcript_file": "speech.txt", "post_context_file": "caption.txt"}]})
        def fake_run(command, folder, name, timeout=300):
            if name == "probe":
                return {"returncode": 0, "stdout": json.dumps({"streams": [{"codec_type": "video"}, {"codec_type": "audio"}], "format": {"duration": "10"}}), "stderr": ""}
            if name == "audio":
                (folder / "audio.wav").write_bytes(b"audio")
            if name.startswith("frame-"):
                (folder / (name + ".jpg")).write_bytes(b"frame")
            return {"returncode": 0, "stdout": "version", "stderr": ""}
        with patch("content_eval.evidence.run", side_effect=fake_run):
            batch = collect(self.path("manifest.json"), self.path("evidence"), 3)
        record = batch["items"][0]
        self.assertEqual(record["preparation"]["status"], "success")
        self.assertEqual(len(record["frames"]["frames"]), 3)
        self.assertEqual(record["transcript"]["provenance"], "user supplied")
        batch_hash = file_hash(self.path("evidence/batch.json"))
        self.path("clip.mp4").unlink()
        with patch("content_eval.evidence.run", side_effect=AssertionError("Must not reprocess")):
            self.assertEqual(collect(self.path("manifest.json"), self.path("evidence"), 3), batch)
        self.assertEqual(file_hash(self.path("evidence/batch.json")), batch_hash)
        (self.path("evidence") / record["id"] / "source.mp4").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "modified saved evidence"):
            collect(self.path("manifest.json"), self.path("evidence"), 3)

    def test_missing_tools_and_missing_file_are_explicit_and_batch_continues(self):
        write(self.path("manifest.json"), {"items": [{"id": "url", "url": "https://example.com/video"}, {"id": "missing", "file": "missing.mp4"}]})
        with patch("content_eval.evidence.shutil.which", return_value=None):
            batch = collect(self.path("manifest.json"), self.path("evidence"))
        self.assertEqual(len(batch["items"]), 2)
        self.assertIn("Missing yt-dlp", batch["items"][0]["retrieval"]["reason"])
        self.assertIn("does not exist", batch["items"][1]["retrieval"]["reason"])
        self.assertTrue(all(i["preparation"]["status"] == "failed" for i in batch["items"]))

    def test_audio_absence_does_not_imply_transcript(self):
        self.path("clip.mp4").write_bytes(b"fixture")
        write(self.path("manifest.json"), {"items": [{"file": "clip.mp4"}]})
        def fake_run(command, folder, name, timeout=300):
            if name == "probe":
                return {"returncode": 0, "stdout": '{"streams":[{"codec_type":"video"}],"format":{"duration":"1"}}', "stderr": ""}
            if name.startswith("frame-"):
                (folder / (name + ".jpg")).write_bytes(b"jpg")
            return {"returncode": 0, "stdout": "", "stderr": ""}
        with patch("content_eval.evidence.run", side_effect=fake_run):
            item = collect(self.path("manifest.json"), self.path("evidence"), 1)["items"][0]
        self.assertEqual(item["audio"]["status"], "absent")
        self.assertEqual(item["transcript"]["status"], "unavailable")
        self.assertEqual(item["preparation"]["status"], "success")

    def test_partial_remote_video_without_audio_cannot_establish_silence(self):
        write(self.path("manifest.json"), {"items": [{"id": "partial", "url": "https://example.com/chosen"}]})
        def fake_retrieve(item, folder):
            media = folder / "source.mp4"
            media.write_bytes(b"video-only fragment")
            return media, {}, status("partial", "Audio download restricted")
        def fake_run(command, folder, name, timeout=300):
            if name == "probe":
                return {"returncode": 0, "stdout": '{"streams":[{"codec_type":"video"}],"format":{"duration":"1"}}', "stderr": ""}
            if name.startswith("frame-"):
                (folder / (name + ".jpg")).write_bytes(b"jpg")
            return {"returncode": 0, "stdout": "", "stderr": ""}
        with patch("content_eval.evidence.retrieve", side_effect=fake_retrieve), patch("content_eval.evidence.run", side_effect=fake_run):
            item = collect(self.path("manifest.json"), self.path("evidence"), 1)["items"][0]
        self.assertIsNone(item["audio_present"])
        self.assertEqual(item["preparation"]["status"], "partial")
        self.assertIn("speech_if_present", item["preparation"]["unmet_requirements"])

    def test_manifest_rejects_traversal_and_duplicate_ids(self):
        for items in ([{"id": "../escape", "file": "clip.mp4"}], [{"id": "same", "file": "a"}, {"id": "same", "file": "b"}]):
            write(self.path("manifest.json"), {"items": items})
            with self.assertRaises(ValueError):
                normalize(self.path("manifest.json"))

    def test_cli_collection_saves_report_templates_and_stable_cache_on_failure(self):
        write(self.path("manifest.json"), {"items": [{"id": "missing", "file": "not-here.mp4"}]})
        command = [sys.executable, "-m", "content_eval", "collect", str(self.path("manifest.json")), "--out", str(self.path("evidence"))]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(self.path("evidence/reference-template.json").is_file())
        self.assertIn("does not exist", self.path("evidence/collection-report.md").read_text())
        original_hash = file_hash(self.path("evidence/batch.json"))
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(file_hash(self.path("evidence/batch.json")), original_hash)

    def test_low_score_fails_and_zero_denominators_are_null(self):
        self.build_scored_fixture()
        scores = read(self.path("scores.json"))
        for question in scores["items"][0]["questions"].values():
            question["label"] = "incorrect"
        write(self.path("scores.json"), scores)
        result = self.score()
        self.assertEqual(result["summary"]["end_to_end_pass"]["numerator"], 0)
        from content_eval.evaluation import metrics
        self.assertIsNone(metrics([])["understanding_score"]["rate"])

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe not on PATH")
    def test_real_ffmpeg_collection_and_saved_source_reuse(self):
        source = self.path("synthetic.mp4")
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                        "testsrc=size=320x240:rate=10", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=16000", "-t", "2", "-c:v", "mpeg4",
                        "-c:a", "aac", str(source)], check=True, capture_output=True)
        write(self.path("manifest.json"), {"items": [{"id": "real", "file": "synthetic.mp4"}]})
        batch = collect(self.path("manifest.json"), self.path("evidence"), 3)
        item = batch["items"][0]
        self.assertEqual(item["frames"]["status"], "success")
        self.assertEqual(len(item["frames"]["frames"]), 3)
        self.assertEqual(item["audio"]["status"], "success")
        self.assertEqual(item["preparation"]["status"], "success")
        source.unlink()
        with patch("content_eval.evidence.run", side_effect=AssertionError("Reprocessing cached media")):
            self.assertEqual(collect(self.path("manifest.json"), self.path("evidence"), 3), batch)


if __name__ == "__main__":
    unittest.main()
