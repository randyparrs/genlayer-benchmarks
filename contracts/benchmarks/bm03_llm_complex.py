# { "Depends": "py-genlayer:test" }
# BM-03: Complex LLM Call
# Long prompt, JSON response required.
# Measures how prompt complexity affects latency and consensus reliability.
# Equivalence Principle: same verdict + confidence ±10 points ✅

import json
from genlayer import *


class BM03LLMComplex(gl.Contract):
    analyses: DynArray[str]

    def __init__(self):
        pass

    @gl.public.write
    def analyze_topic(self, topic: str) -> str:
        def leader_fn():
            prompt = f"""Analyze this topic and respond ONLY with a JSON object.
Topic: "{topic}"

{{"verdict": "POSITIVE", "confidence": 80, "summary": "one sentence"}}

Rules:
- verdict: exactly POSITIVE, NEGATIVE, or NEUTRAL
- confidence: integer 0-100
- summary: one sentence max
No extra text."""
            result = gl.nondet.exec_prompt(prompt)
            clean = result.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            verdict = data.get("verdict", "NEUTRAL")
            confidence = int(data.get("confidence", 50))
            summary = data.get("summary", "")
            if verdict not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                verdict = "NEUTRAL"
            confidence = max(0, min(100, confidence))
            return json.dumps({"verdict": verdict, "confidence": confidence, "summary": summary}, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                if leader_data["verdict"] != validator_data["verdict"]:
                    return False
                return abs(leader_data["confidence"] - validator_data["confidence"]) <= 10
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.analyses.append(topic[:30])
        return raw

    @gl.public.view
    def get_count(self) -> u256:
        return u256(len(self.analyses))
