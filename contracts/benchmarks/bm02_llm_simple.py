# { "Depends": "py-genlayer:test" }
# BM-02: Simple LLM Call
# Short prompt, deterministic expected output.
# Measures baseline LLM latency and consensus time.
# Equivalence Principle: output must match exactly

from genlayer import *


class BM02LLMSimple(gl.Contract):
    results: DynArray[str]

    def __init__(self):
        pass

    @gl.public.write
    def classify_sentiment(self, text: str) -> str:
        def leader_fn():
            prompt = f"""Classify the sentiment of this text.
Text: "{text}"
Respond ONLY with one word: POSITIVE, NEGATIVE, or NEUTRAL.
No other text."""
            result = gl.nondet.exec_prompt(prompt)
            sentiment = result.strip().upper()
            if sentiment not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                sentiment = "NEUTRAL"
            return sentiment

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_out = leader_fn()
                return leader_result.calldata.strip() == validator_out.strip()
            except Exception:
                return False

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.results.append(f"{text[:30]}:{result}")
        return result

    @gl.public.view
    def get_results(self) -> u256:
        return u256(len(self.results))
