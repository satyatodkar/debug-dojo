import os
import unittest
from unittest.mock import patch, MagicMock
import httpx

from ai_agent import (
    supabase,
    start_challenge_session,
    evaluate_submission,
    check_guardrails,
    count_code_lines,
    validate_guardrail_policy,
    validate_submission_input,
    construct_tutor_prompt,
    log_agent_audit,
    get_configured_ai_provider,
    call_ai_tutor,
    DEFAULT_GUARDRAIL_POLICY,
    DEFAULT_GUARDRAIL_POLICY_VERSION,
    SAFE_FALLBACK_MESSAGE,
    MOCK_MODEL_IDENTIFIER,
    ConfigurationError,
    ModelProviderError,
    AuditLoggingError,
    UnauthorizedSessionError,
    ExaminationRestrictionError,
)
from challenges import HIDDEN_TESTS


class TestAITutorGuardrailsAndAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_learner = "test_learner_suite"
        cls.test_challenge = "count_even_numbers"
        # Start a real active session in Supabase for integration tests
        cls.session_id, cls.guardrails = start_challenge_session(cls.test_learner, cls.test_challenge)

    # --------------------------------------------------------------------------
    # 1. Valid default guardrails are applied when no challenge-specific policy exists
    # --------------------------------------------------------------------------
    def test_01_valid_default_guardrails_applied(self):
        policy = validate_guardrail_policy(None)
        self.assertIsInstance(policy, dict)
        self.assertEqual(policy["version"], DEFAULT_GUARDRAIL_POLICY_VERSION)
        self.assertTrue(len(policy["forbidden_keywords"]) > 0)
        self.assertTrue(policy["block_direct_solution"])
        self.assertEqual(policy["max_revealed_code_lines"], 3)
        self.assertIn("here is the exact code", policy["forbidden_keywords"])

    # --------------------------------------------------------------------------
    # 2. Challenge-specific policy overrides work correctly
    # --------------------------------------------------------------------------
    def test_02_challenge_specific_policy_overrides(self):
        custom_override = {
            "forbidden_keywords": ["custom_leak_keyword"],
            "max_revealed_code_lines": 1,
            "version": "2026.override.1"
        }
        policy = validate_guardrail_policy(custom_override)
        self.assertEqual(policy["max_revealed_code_lines"], 1)
        self.assertIn("custom_leak_keyword", policy["forbidden_keywords"])
        # Baseline default keywords must still be retained
        self.assertIn("here is the exact code", policy["forbidden_keywords"])
        self.assertEqual(policy["version"], "2026.override.1")

    # --------------------------------------------------------------------------
    # 3. Invalid or missing policies fail safely
    # --------------------------------------------------------------------------
    def test_03_invalid_or_missing_policies_fail_safely(self):
        # Empty dict should NEVER mean unrestricted access
        p_empty = validate_guardrail_policy({})
        self.assertTrue(p_empty["block_direct_solution"])
        self.assertTrue(len(p_empty["forbidden_keywords"]) > 0)
        self.assertEqual(p_empty["max_revealed_code_lines"], 3)

        # Malformed settings
        malformed = {
            "forbidden_keywords": "not-a-list",
            "max_revealed_code_lines": "not-an-int",
            "block_direct_solution": "not-a-bool",
        }
        p_repaired = validate_guardrail_policy(malformed)
        self.assertIsInstance(p_repaired["forbidden_keywords"], list)
        self.assertIsInstance(p_repaired["max_revealed_code_lines"], int)
        self.assertIsInstance(p_repaired["block_direct_solution"], bool)

    # --------------------------------------------------------------------------
    # 4. A normal real-model response is validated and logged
    # --------------------------------------------------------------------------
    def test_04_normal_real_model_response_validated_and_logged(self):
        real_model_response = (
            "Great effort! Notice your loop condition: Python lists are indexed from 0 to len - 1. "
            "What happens if your loop index accesses len(numbers)? Try checking the range."
        )
        fake_usage = {"prompt_tokens": 150, "completion_tokens": 42, "total_tokens": 192}

        # Mock real provider invocation returning valid progressive hint
        with patch("ai_agent._call_gemini_provider", return_value=(real_model_response, fake_usage)):
            feedback = evaluate_submission(
                session_id=self.session_id,
                learner_id=self.test_learner,
                challenge_id=self.test_challenge,
                user_code="def count_even_numbers(numbers): pass",
                guardrails=self.guardrails,
                provider="gemini",
                verify_session=False,
            )

        self.assertEqual(feedback, real_model_response)

        # Confirm Supabase audit record
        res = (
            supabase.table("agent_audit_logs")
            .select("*")
            .eq("learner_id", self.test_learner)
            .eq("challenge_id", self.test_challenge)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        self.assertTrue(len(res.data) > 0)
        record = res.data[0]
        meta = record.get("metadata", {})
        self.assertFalse(meta.get("is_mock"))
        self.assertEqual(meta.get("provider"), "gemini")
        self.assertEqual(meta.get("token_usage"), fake_usage)
        self.assertTrue(record.get("guardrail_passed"))

    # --------------------------------------------------------------------------
    # 5. Forbidden-keyword and code-line checks work
    # --------------------------------------------------------------------------
    def test_05_forbidden_keyword_and_code_line_checks(self):
        # Case 1: Forbidden keyword (mixed case)
        text_keyword = "Sure! Here is the EXACT code: def count_even_numbers(): return 0"
        passed_kw, flags_kw, _ = check_guardrails(text_keyword, self.guardrails, self.test_challenge)
        self.assertFalse(passed_kw)
        self.assertIn("forbidden_keyword_detected", flags_kw.get("violations", []))

        # Case 2: Code line counting (> max_revealed_code_lines which is 3)
        text_lines = (
            "Here is a snippet:\n"
            "```python\n"
            "line_one = 1\n"
            "line_two = 2\n"
            "line_three = 3\n"
            "line_four = 4\n"
            "```"
        )
        self.assertEqual(count_code_lines(text_lines), 4)
        passed_lines, flags_lines, _ = check_guardrails(text_lines, self.guardrails, self.test_challenge)
        self.assertFalse(passed_lines)
        self.assertIn("excessive_code_lines_revealed", flags_lines.get("violations", []))

    # --------------------------------------------------------------------------
    # 6. A response rejected by guardrails is never delivered to the learner
    # --------------------------------------------------------------------------
    def test_06_rejected_response_never_delivered_to_learner(self):
        leaked_response = (
            "Here is the solution:\n"
            "def count_even_numbers(numbers):\n"
            "    return len([n for n in numbers if n % 2 == 0])\n"
        )
        feedback = evaluate_submission(
            session_id=self.session_id,
            learner_id=self.test_learner,
            challenge_id=self.test_challenge,
            user_code="def count_even_numbers(numbers): pass",
            guardrails=self.guardrails,
            mock_response=leaked_response,
            verify_session=False,
        )

        # Learner MUST receive the safe fallback, NEVER the leaked response
        self.assertEqual(feedback, SAFE_FALLBACK_MESSAGE)
        self.assertNotIn("Here is the solution", feedback)
        self.assertNotIn("count_even_numbers", feedback)

    # --------------------------------------------------------------------------
    # 7. Model timeouts and provider errors are handled without silently switching to mock
    # --------------------------------------------------------------------------
    def test_07_provider_errors_raise_without_silent_mock_fallback(self):
        # Timeout error
        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timeout after 10s")):
            with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123"}):
                with self.assertRaises(ModelProviderError) as ctx:
                    evaluate_submission(
                        session_id=self.session_id,
                        learner_id=self.test_learner,
                        challenge_id=self.test_challenge,
                        user_code="def foo(): pass",
                        provider="gemini",
                        verify_session=False,
                    )
                self.assertIn("timed out", str(ctx.exception).lower())

        # HTTP error
        mock_resp = MagicMock(status_code=500, text="Internal Server Error")
        with patch("httpx.Client.post", return_value=mock_resp):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "fake_key_456"}):
                with self.assertRaises(ModelProviderError):
                    evaluate_submission(
                        session_id=self.session_id,
                        learner_id=self.test_learner,
                        challenge_id=self.test_challenge,
                        user_code="def foo(): pass",
                        provider="openai",
                        verify_session=False,
                    )

    # --------------------------------------------------------------------------
    # 8. Missing API credentials produce a clear configuration error
    # --------------------------------------------------------------------------
    def test_08_missing_api_credentials_produce_clear_error(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
            with self.assertRaises(ConfigurationError) as ctx:
                evaluate_submission(
                    session_id=self.session_id,
                    learner_id=self.test_learner,
                    challenge_id=self.test_challenge,
                    user_code="def foo(): pass",
                    provider="gemini",
                    verify_session=False,
                )
            self.assertIn("GEMINI_API_KEY", str(ctx.exception))

        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaises(ConfigurationError) as ctx:
                evaluate_submission(
                    session_id=self.session_id,
                    learner_id=self.test_learner,
                    challenge_id=self.test_challenge,
                    user_code="def foo(): pass",
                    provider="openai",
                    verify_session=False,
                )
            self.assertIn("OPENAI_API_KEY", str(ctx.exception))

    # --------------------------------------------------------------------------
    # 9. Mock and real-model records are distinguished in Supabase
    # --------------------------------------------------------------------------
    def test_09_mock_and_real_model_records_distinguished(self):
        # 1. Run mock evaluation
        evaluate_submission(
            session_id=self.session_id,
            learner_id=self.test_learner,
            challenge_id=self.test_challenge,
            user_code="def count_even_numbers(numbers): pass",
            provider="mock",
            verify_session=False,
        )

        res_mock = (
            supabase.table("agent_audit_logs")
            .select("*")
            .eq("learner_id", self.test_learner)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        mock_rec = res_mock.data[0]
        self.assertTrue(mock_rec["metadata"]["is_mock"])
        self.assertEqual(mock_rec["metadata"]["model"], MOCK_MODEL_IDENTIFIER)

        # 2. Run real model evaluation (mocked provider output)
        fake_usage = {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130}
        with patch("ai_agent._call_gemini_provider", return_value=("Check your loop counter.", fake_usage)):
            evaluate_submission(
                session_id=self.session_id,
                learner_id=self.test_learner,
                challenge_id=self.test_challenge,
                user_code="def count_even_numbers(numbers): pass",
                provider="gemini",
                verify_session=False,
            )

        res_real = (
            supabase.table("agent_audit_logs")
            .select("*")
            .eq("learner_id", self.test_learner)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        real_rec = res_real.data[0]
        self.assertFalse(real_rec["metadata"]["is_mock"])
        self.assertEqual(real_rec["metadata"]["provider"], "gemini")

    # --------------------------------------------------------------------------
    # 10. Token usage is stored only when returned by the provider
    # --------------------------------------------------------------------------
    def test_10_token_usage_stored_only_when_returned(self):
        # Mock mode: token_usage MUST be None (no fake invented numbers)
        evaluate_submission(
            session_id=self.session_id,
            learner_id=self.test_learner,
            challenge_id=self.test_challenge,
            user_code="def count_even_numbers(numbers): pass",
            provider="mock",
            verify_session=False,
        )
        res_mock = (
            supabase.table("agent_audit_logs")
            .select("*")
            .eq("learner_id", self.test_learner)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        self.assertIsNone(res_mock.data[0]["metadata"]["token_usage"])

        # Real mode: token usage dict stored as returned
        actual_tokens = {"prompt_tokens": 204, "completion_tokens": 56, "total_tokens": 260}
        with patch("ai_agent._call_openai_provider", return_value=("Check indentation.", actual_tokens)):
            evaluate_submission(
                session_id=self.session_id,
                learner_id=self.test_learner,
                challenge_id=self.test_challenge,
                user_code="def count_even_numbers(numbers): pass",
                provider="openai",
                verify_session=False,
            )
        res_real = (
            supabase.table("agent_audit_logs")
            .select("*")
            .eq("learner_id", self.test_learner)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        self.assertEqual(res_real.data[0]["metadata"]["token_usage"], actual_tokens)

    # --------------------------------------------------------------------------
    # 11. Supabase audit inserts are confirmed before success is reported
    # --------------------------------------------------------------------------
    def test_11_audit_insert_confirmed_before_reporting_success(self):
        mock_failing_client = MagicMock()
        mock_table = MagicMock()
        mock_insert = MagicMock()
        mock_insert.execute.side_effect = Exception("DB Connection Refused")
        mock_table.insert.return_value = mock_insert
        mock_failing_client.table.return_value = mock_table

        with self.assertRaises(AuditLoggingError) as ctx:
            log_agent_audit(
                client=mock_failing_client,
                session_id=self.session_id,
                learner_id=self.test_learner,
                challenge_id=self.test_challenge,
                input_prompt="test",
                output_content="test",
                guardrail_passed=True,
                guardrail_flags={},
            )
        self.assertIn("Failed to insert audit record", str(ctx.exception))

    # --------------------------------------------------------------------------
    # 12. Hidden-test information is not included in model requests or messages
    # --------------------------------------------------------------------------
    def test_12_hidden_tests_never_included_in_prompts(self):
        _, input_prompt = construct_tutor_prompt(
            learner_id=self.test_learner,
            challenge_id="count_even_numbers",
            user_code="def count_even_numbers(numbers): pass"
        )
        
        # Verify none of the hidden test inputs/outputs for count_even_numbers leak into the prompt
        hidden_cases = HIDDEN_TESTS.get("count_even_numbers", [])
        self.assertTrue(len(hidden_cases) > 0)
        for case in hidden_cases:
            case_args_str = str(case.get("args", ""))
            if len(case_args_str) > 5:
                self.assertNotIn(case_args_str, input_prompt)

    # --------------------------------------------------------------------------
    # 13. Unauthorized learners cannot access another user's session
    # --------------------------------------------------------------------------
    def test_13_unauthorized_learners_cannot_access_session(self):
        # session_id belongs to self.test_learner
        impostor_learner = "impostor_student_999"
        with self.assertRaises(UnauthorizedSessionError):
            evaluate_submission(
                session_id=self.session_id,
                learner_id=impostor_learner,
                challenge_id=self.test_challenge,
                user_code="def count_even_numbers(numbers): pass",
                verify_session=True,
            )

    # --------------------------------------------------------------------------
    # 14. Examination sessions cannot access general AI tutoring
    # --------------------------------------------------------------------------
    def test_14_exam_sessions_cannot_access_ai_tutoring(self):
        exam_session_id, _ = start_challenge_session(
            learner_id="exam_candidate_1",
            challenge_id=self.test_challenge,
            session_type="exam",
            is_exam=True,
        )
        try:
            with self.assertRaises(ExaminationRestrictionError):
                evaluate_submission(
                    session_id=exam_session_id,
                    learner_id="exam_candidate_1",
                    challenge_id=self.test_challenge,
                    user_code="def count_even_numbers(numbers): pass",
                    verify_session=True,
                )
        finally:
            supabase.table("agent_sessions").delete().eq("id", exam_session_id).execute()

    # --------------------------------------------------------------------------
    # 15. Existing session creation and audit-logging tests continue to pass
    # --------------------------------------------------------------------------
    def test_15_existing_session_and_audit_flow_intact(self):
        sample_code = """def count_even_numbers(numbers):
    count = 0
    for i in range(len(numbers) + 1):  # Boundary error
        if numbers[i] % 2 == 0: count += 1
    return count
"""
        feedback = evaluate_submission(
            session_id=self.session_id,
            learner_id=self.test_learner,
            challenge_id=self.test_challenge,
            user_code=sample_code,
            guardrails=self.guardrails,
            provider="mock",
            verify_session=True,
        )
        self.assertIn("[MOCK AI TUTOR]", feedback)
        self.assertIn("range", feedback)


if __name__ == "__main__":
    unittest.main()
