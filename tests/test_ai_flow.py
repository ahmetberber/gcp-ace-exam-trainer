"""Claude API çağrılarını sahte istemciyle test eder (ağ/anahtar gerekmez)."""
import types
import unittest
from unittest import mock

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

from examtrainer import ai

Q = {"question": "Soru?", "options": ["a", "b", "c", "d"], "correct": [1], "explanation": "e",
     "domain": 2, "topic": "Compute Engine", "difficulty": "orta", "source_url": "https://cloud.google.com/x"}


def msg(stop, blocks):
    return types.SimpleNamespace(stop_reason=stop, content=blocks)


class FakeStream:
    def __init__(self, m):
        self.m = m

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        for b in self.m.content:
            yield types.SimpleNamespace(type="content_block_start", content_block=b)

    def get_final_message(self):
        return self.m


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(stream=self._stream))

    def _stream(self, **kw):
        self.calls.append(kw)
        return FakeStream(self.replies.pop(0))


SETTINGS = {"api_key": "x", "model": "claude-opus-5-5", "effort": "medium", "web_search": True, "language": "tr"}


@unittest.skipIf(anthropic is None, "anthropic kurulu değil")
class AIFlowTests(unittest.TestCase):
    def run_with(self, replies):
        fc = FakeClient(replies)
        with mock.patch.object(ai, "_client", return_value=(anthropic, fc)):
            return fc, ai.generate_questions(SETTINGS, "ACE", 1, progress=lambda m: None)

    def test_pause_then_submit(self):
        search = types.SimpleNamespace(type="server_tool_use", name="web_search")
        submit = types.SimpleNamespace(type="tool_use", name="submit_questions", input={"questions": [Q]})
        fc, qs = self.run_with([msg("pause_turn", [search]), msg("tool_use", [submit])])
        self.assertEqual(len(qs), 1)
        self.assertEqual(qs[0]["source"], "ai")
        self.assertEqual(len(fc.calls), 2)
        first = fc.calls[0]
        self.assertEqual(first["model"], "claude-opus-5-5")
        self.assertEqual(first["fallbacks"], "default")
        self.assertEqual(first["tools"][0]["type"], "web_search_20260209")
        # pause_turn sonrası asistan içeriği aynen geri gönderilmeli, ek kullanıcı mesajı olmadan
        self.assertEqual(fc.calls[1]["messages"][-1]["role"], "assistant")

    def test_refusal(self):
        with self.assertRaises(ai.AIError):
            self.run_with([msg("refusal", [])])

    def test_nudge_when_no_tool_call(self):
        text = types.SimpleNamespace(type="text", text="hazırladım")
        submit = types.SimpleNamespace(type="tool_use", name="submit_questions", input={"questions": [Q]})
        fc, qs = self.run_with([msg("end_turn", [text]), msg("tool_use", [submit])])
        self.assertEqual(fc.calls[1]["messages"][-1]["role"], "user")
        self.assertEqual(len(qs), 1)

    def test_tool_schema_is_strict(self):
        schema = ai.SUBMIT_TOOL["input_schema"]["properties"]["questions"]["items"]
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(schema["properties"]))


if __name__ == "__main__":
    unittest.main()
