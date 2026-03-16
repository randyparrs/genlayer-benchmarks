# contracts/benchmarks/bm06_validator_scaling.py
from genlayer import IContract, public
import json

class BM06ValidatorScaling(IContract):
    """
    Benchmark 06: Validator scaling test.
    Same operation run with 1, 3, 5, 7, and 10 validators.
    Run this contract with different Studio validator configurations.
    """

    def __init__(self):
        self.results: list = []

    @public
    def scaling_test_operation(self, validator_count: int) -> dict:
        prompt = """
Rate the quality of this sentence on a scale of 1-10:
"The quick brown fox jumps over the lazy dog."
Respond with only a JSON object: {"score": <integer 1-10>}
EQUIVALENCE NOTE: Scores within 2 points are equivalent.
"""
        result_text = call_llm(prompt)
        try:
            result = json.loads(result_text.strip())
            score = result.get("score", 0)
        except Exception:
            score = 0
        entry = {"validator_count": validator_count, "score": score}
        self.results.append(entry)
        return entry
