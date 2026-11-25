import json
import tempfile
import unittest
from pathlib import Path

from examtrainer.engine import build_session
from examtrainer.exams import EXAMS
from examtrainer.store import QuestionBank, Stats, ValidationError, validate_question

ROOT = Path(__file__).resolve().parent.parent


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bank = QuestionBank(ROOT / "questions", self.tmp)
        self.stats = Stats(self.tmp)

    def test_builtin_bank_valid(self):
        self.assertEqual(self.bank.load_errors, [])
        qs = self.bank.for_exam("ACE")
        self.assertGreaterEqual(len(qs), 80)
        self.assertEqual({q["domain"] for q in qs}, set(EXAMS["ACE"].domains))
        for q in qs:
            self.assertIn(q["topic"], EXAMS["ACE"].topics, q["id"])
        ids = [q["id"] for q in qs]
        self.assertEqual(len(ids), len(set(ids)))

    def test_shuffle_keeps_correct_answer(self):
        s = build_session(self.bank, self.stats, "ACE", 30, seed=1)
        for i, it in enumerate(s.items):
            correct_texts = {it.q["options"][c] for c in it.q["correct"]}
            self.assertEqual({it.options[d] for d in it.correct}, correct_texts)
            self.assertTrue(s.answer(i, it.correct))
        summary = s.finish(self.stats)
        self.assertEqual(summary["percent"], 100)
        self.assertTrue(summary["passed"])
        self.assertTrue((self.tmp / "stats.json").exists())

    def test_exam_mode_distribution_and_timer(self):
        s = build_session(self.bank, self.stats, "ACE", 50, mode="sinav", seed=2)
        self.assertEqual(len(s.items), 50)
        self.assertEqual(len({it.q["id"] for it in s.items}), 50)
        self.assertEqual(s.time_limit, 120 * 60)
        doms = [it.q["domain"] for it in s.items]
        self.assertGreater(doms.count(2), doms.count(1))

    def test_weak_focus(self):
        s = build_session(self.bank, self.stats, "ACE", 5, seed=3)
        s.answer(0, {99})  # yanlış
        s.finish(self.stats)
        weak = build_session(self.bank, self.stats, "ACE", 10, focus="zayif")
        self.assertEqual([it.q["id"] for it in weak.items], [s.items[0].q["id"]])

    def test_topic_filter(self):
        s = build_session(self.bank, self.stats, "ACE", 100, topics=["GKE (Kubernetes)"])
        self.assertTrue(all(it.q["topic"] == "GKE (Kubernetes)" for it in s.items))

    def test_validation_and_import(self):
        with self.assertRaises(ValidationError):
            validate_question({"question": "x", "options": ["a", "b"], "correct": [5]}, "ACE")
        good = {"question": "Yeni soru?", "options": ["a", "b", "c", "d"], "correct": [2],
                "domain": 2, "explanation": "çünkü"}
        added, errors = self.bank.add_user_questions([good, good], "ACE")
        self.assertEqual((added, len(errors)), (1, 1))
        stored = json.loads((self.tmp / "user_questions.json").read_text(encoding="utf-8"))
        self.assertEqual(len(stored), 1)
        again = QuestionBank(ROOT / "questions", self.tmp)
        self.assertEqual(again.count("ACE")["eklenen"], 1)
        self.assertTrue(again.delete_user_question(stored[0]["id"]))


if __name__ == "__main__":
    unittest.main()
