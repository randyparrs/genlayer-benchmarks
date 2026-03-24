# { "Depends": "py-genlayer:test" }
# BM-06: Validator Scaling Test
# Same operation run to measure how performance changes
# as the number of validators increases.
# Run this contract with different Studio validator configurations.
# Equivalence Principle: scores within ±2 points ✅

import json
from genlayer import *


class BM06ValidatorScaling(gl.Contract):
    results: DynArray[str]
    run_count: u256

    def __init__(self):
        self.run_count = u256(0)

    @gl.public.write
    def scaling_test(self, validator_count: u256) -> str:
        def leader_fn():
            prompt = """Rate the quality of this sentence on a scale of 1-10:
"The quick brown fox jumps over the lazy dog."
Respond ONLY with a JSON object: {"score": 8}
No extra text."""
            result = gl.nondet.exec_prompt(prompt)
            clean = result.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            score = int(data.get("score", 5))
            score = max(1, min(10, score))
            return json.dumps({"score": score, "validator_count": int(validator_count)}, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                # Scores within ±2 points are equivalent ✅
                return abs(leader_data["score"] - validator_data["score"]) <= 2
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        data = json.loads(raw)
        entry = f"validators:{int(validator_count)} score:{data['score']}"
        self.results.append(entry)
        self.run_count = u256(int(self.run_count) + 1)
        return raw

    @gl.public.view
    def get_run_count(self) -> u256:
        return self.run_count

    @gl.public.view
    def get_last_result(self) -> str:
        count = len(self.results)
        if count == 0:
            return "No results yet"
        return self.results[count - 1]

