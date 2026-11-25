"""Offline tests for the Claude adapter: a fake client stands in for the API (no spend)."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from module_platform.providers import AnthropicProvider, ModelRequest, ProviderError
from module_platform.providers.anthropic_provider import cost_usd


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    def __init__(self, text='{"ok": true}', stop="end_turn", usage=None):
        self.calls = []
        usage = usage or dict(input_tokens=1000, output_tokens=500, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        self.message = SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop, usage=SimpleNamespace(**usage))
        self.messages = self

    def stream(self, **params):
        self.calls.append(params)
        return FakeStream(self.message)


def request(tier="fast", key="design_spec"):
    return ModelRequest("r1", "builder", "system", ({"role": "user", "content": "hi"},), metadata={"json": True, "tier": tier, "key": key})


class AnthropicProviderTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def provider(self, client, budget=10.0, model="claude-sonnet-5-5"):
        return AnthropicProvider(api_key="test", model=model, ledger_path=self.dir / "spend.json", budget=budget, client=client)

    def test_tiers_pick_models_and_json_is_parsed(self):
        client = FakeClient()
        provider = self.provider(client)
        fast = provider.generate(request("fast"))
        strong = provider.generate(request("strong"))
        self.assertEqual(client.calls[0]["model"], "claude-haiku-5-5")
        self.assertEqual(client.calls[1]["model"], "claude-sonnet-5-5")
        self.assertEqual(fast.structured_output, {"ok": True})
        self.assertEqual(strong.provider_metadata["model"], "claude-sonnet-5-5")

    def test_non_claude_model_name_falls_back_to_sonnet(self):
        provider = self.provider(FakeClient(), model="gpt-4.1-mini")
        self.assertEqual(provider._model_for("strong"), "claude-sonnet-5-5")

    def test_cost_matches_price_table(self):
        usage = dict(input_tokens=1_000_000, output_tokens=1_000_000, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        self.assertAlmostEqual(cost_usd("claude-sonnet-5-5", usage), 12.0)
        self.assertAlmostEqual(cost_usd("claude-opus-5-5", usage), 24.0)
        self.assertGreater(cost_usd("unknown-model", usage), cost_usd("claude-sonnet-5-5", usage))

    def test_budget_stops_calls_and_survives_restart(self):
        usage = dict(input_tokens=1_000_000, output_tokens=0, cache_creation_input_tokens=0, cache_read_input_tokens=0)
        provider = self.provider(FakeClient(usage=usage), budget=1.0)
        provider.generate(request("strong"))  # $2 spent, over the $1 cap
        with self.assertRaises(ProviderError) as caught:
            provider.generate(request("strong"))
        self.assertIn("budget", str(caught.exception))
        again = self.provider(FakeClient(), budget=1.0)
        with self.assertRaises(ProviderError):
            again.generate(request("strong"))

    def test_truncated_and_empty_replies_are_errors(self):
        with self.assertRaises(ProviderError):
            self.provider(FakeClient(stop="max_tokens")).generate(request())
        with self.assertRaises(ProviderError):
            self.provider(FakeClient(text="")).generate(request())

    def test_fast_tier_turns_thinking_off_and_strong_keeps_default(self):
        client = FakeClient()
        provider = self.provider(client)
        provider.generate(request("fast"))
        provider.generate(request("strong"))
        self.assertEqual(client.calls[0]["thinking"], {"type": "disabled"})
        self.assertNotIn("thinking", client.calls[1])

    def test_truncated_reply_is_saved_for_diagnosis(self):
        debug = self.dir / "debug"
        provider = AnthropicProvider(api_key="t", model="claude-sonnet-5-5", ledger_path=self.dir / "s.json", budget=5, client=FakeClient(text="partial {", stop="max_tokens"), debug_dir=debug)
        with self.assertRaises(ProviderError):
            provider.generate(request("fast", key="file_set:build"))
        saved = list(debug.glob("*truncated.txt"))
        self.assertEqual(len(saved), 1)
        self.assertIn("partial {", saved[0].read_text())

    def test_missing_key_is_a_clear_error(self):
        with self.assertRaises(ProviderError):
            AnthropicProvider(api_key="", budget=1.0, ledger_path=self.dir / "x.json").generate(request())


if __name__ == "__main__":
    unittest.main()
