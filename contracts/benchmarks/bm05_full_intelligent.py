# { "Depends": "py-genlayer:test" }
# BM-05: Full Intelligent Contract
# Web fetch + LLM call in a single transaction.
# Most representative of real production usage.
# Equivalence Principle: same verdict + confidence ±15 points ✅

import json
from genlayer import *


class BM05FullIntelligent(gl.Contract):
    verdicts: DynArray[str]

    def __init__(self):
        pass

    @gl.public.write
    def evaluate_claim(self, claim: str, source_url: str) -> str:
        def leader_fn():
            response = gl.nondet.web.get(source_url)
            web_content = response.body.decode("utf-8")[:2000]

            prompt = f"""You are a fact-checker. Evaluate this claim using only the source provided.

Claim: "{claim}"
Source ({source_url}):
{web_content}

Respond ONLY with a JSON object:
{{"verdict": "TRUE", "confidence": 85, "reasoning": "one sentence from the source"}}

Rules:
- verdict: exactly TRUE, FALSE, or UNVERIFIABLE
- confidence: integer 0-100
- reasoning: one sentence citing the source
No extra text."""
            result = gl.nondet.exec_prompt(prompt)
            clean = result.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)
            verdict = data.get("verdict", "UNVERIFIABLE")
            confidence = int(data.get("confidence", 50))
            reasoning = data.get("reasoning", "")
            if verdict not in ("TRUE", "FALSE", "UNVERIFIABLE"):
                verdict = "UNVERIFIABLE"
            confidence = max(0, min(100, confidence))
            return json.dumps({"verdict": verdict, "confidence": confidence, "reasoning": reasoning}, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                if leader_data["verdict"] != validator_data["verdict"]:
                    return False
                return abs(leader_data["confidence"] - validator_data["confidence"]) <= 15
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        data = json.loads(raw)
        self.verdicts.append(f"{claim[:30]}:{data['verdict']}")
        return raw

    @gl.public.view
    def get_count(self) -> u256:
        return u256(len(self.verdicts))
