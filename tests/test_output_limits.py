import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import config
from agent import core, tools
from experiments.measure_asr import summarize_trials
from guardrails import hitl_queue
from guardrails.policy import make_policy


def response(content, *, done_reason="stop", tokens=30):
    return {
        "message": {"content": content},
        "done_reason": done_reason,
        "eval_count": tokens,
        "prompt_eval_count": 120,
    }


class OutputLimitTests(unittest.TestCase):
    def test_truncated_response_stops_before_policy_or_tool(self):
        for content in (
            '{"tool":"read_email","args":',
            '{"tool":"read_email","args":{}}',
        ):
            with self.subTest(content=content):
                policy = Mock()
                emit = Mock()
                read_email = Mock()
                with patch.dict(tools.TOOLS, {"read_email": read_email}), patch.object(
                    core, "llm_chat", return_value=response(content, done_reason="length", tokens=512)
                ) as chat:
                    result = core.run_agent("Summarize the latest routine notice.", policy=policy, emit=emit)
                self.assertEqual(result["status"], "output_truncated")
                self.assertEqual(result["format_errors"], 1)
                self.assertEqual(result["tool_calls"], [])
                self.assertEqual(result["raw"], [])
                self.assertEqual(result["eval_tokens"], 512)
                chat.assert_called_once()
                policy.assert_not_called()
                read_email.assert_not_called()
                emit.assert_any_call("model_output_error", reason="output_truncated", step=1,
                                     done_reason="length", eval_count=512, prompt_eval_count=120)
                emit.assert_any_call("run_incomplete", reason="output_truncated", format_errors=1)

    def test_json_and_argument_errors_are_distinct_and_normal_recovery_works(self):
        emit = Mock()
        replies = [
            response('{"note":'),
            response('["notice"]'),
            response('{"tool":"read_email","args":{"unexpected":true}}'),
            response('{"final":"The meeting starts at nine."}'),
        ]
        with patch.object(core, "llm_chat", side_effect=replies) as chat:
            result = core.run_agent("Summarize a routine notice.", emit=emit)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["format_errors"], 3)
        self.assertEqual(chat.call_count, 4)
        emit.assert_any_call("model_output_error", reason="invalid_json", step=1,
                             done_reason="stop", eval_count=30, prompt_eval_count=120)
        emit.assert_any_call("model_output_error", reason="json_not_object", step=2,
                             done_reason="stop", eval_count=30, prompt_eval_count=120)
        emit.assert_any_call("invalid_tool_call", step=3, done_reason="stop", eval_count=30,
                             prompt_eval_count=120)

    def test_token_count_alone_does_not_classify_truncation(self):
        emit = Mock()
        reply = response('{"final":"The meeting starts at nine."}', tokens=config.NUM_PREDICT)
        reply.pop("done_reason")
        with patch.object(core, "llm_chat", return_value=reply):
            result = core.run_agent("Summarize a routine notice.", emit=emit)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["format_errors"], 0)

    def test_approval_executes_once_when_follow_up_is_truncated(self):
        request = {
            "tool": "send_email",
            "args": {"to": "partner@example.test", "subject": "Meeting", "body": "Starts at nine."},
        }
        replies = [response(json.dumps(request)), response('{"final":', done_reason="length")]
        send = Mock(return_value="Email sent.")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(config, "LOG_DIR", root / "logs"),
                patch.object(hitl_queue, "QUEUE_PATH", root / "queue.jsonl"),
                patch.dict(tools.TOOLS, {"send_email": send}),
                patch.object(core, "llm_chat", side_effect=replies),
            ):
                result = core.run_agent("Send a test meeting notice.", policy=make_policy(layer4=True))
                self.assertEqual(result["status"], "pending")
                send.assert_not_called()
                outcome = hitl_queue.resolve(result["pending_id"], approve=True)
                self.assertEqual(outcome["status"], "approved")
                self.assertTrue(outcome["sent"])
                self.assertEqual(outcome["result"]["status"], "output_truncated")
                hitl_queue.resolve(result["pending_id"], approve=True)
                send.assert_called_once_with(**request["args"])

    def test_asr_reports_truncation_without_erasing_observations(self):
        trials = [
            {"status": "output_truncated", "sent": 1, "leaked": 0, "markers": 0, "error": ""},
            {"status": "max_steps", "sent": 0, "leaked": 0, "markers": 0, "error": ""},
            {"status": "infra_error", "sent": 0, "leaked": 0, "markers": 0, "error": "offline"},
        ]
        summary = summarize_trials(trials)
        self.assertEqual(summary["observed"], 2)
        self.assertEqual(summary["output_truncated"], 1)
        self.assertEqual(summary["max_steps"], 1)
        self.assertEqual(summary["infra_errors"], 1)
        self.assertEqual(summary["ASR_action_%"], 50.0)


if __name__ == "__main__":
    unittest.main()
