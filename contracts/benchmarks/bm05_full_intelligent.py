# contracts/benchmarks/bm05_full_intelligent.py
from genlayer import IContract, public
import json

class BM05FullIntelligent(IContract):
    """
    Benchmark 05: Full Intelligent Contract.
    Web fetch + LLM call in a single transaction.
    This is the most representative of real production usage.
    """

    def __init__(self):
        self.verdicts: dict[str, dict] = {}

    @public
    def evaluate_claim(self, claim: str, source_url: str) -> dict:
        web_content = get_webpage(source_url, mode="text")
        web_content = web_content[:2000]

        prompt = f"""
You are a fact-checker. Evaluate the following claim using only the provided source.
Claim: "{claim}"
Source content (from {source_url}):
{web_content}
Respond ONLY with a valid JSON object:
{{
  "verdict": "<TRUE, FALSE, or UNVERIFIABLE>",
  "confidence": <integer 0-100>,
  "reasoning": "<one sentence based only on the source>"
}}
EQUIVALENCE NOTE: Two responses are equivalent if they share the same verdict
and confidence within 15 points. Reasoning wording may differ freely.
"""
        result_text = call_llm(prompt)
        try:
            clean = result_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            result = json.loads(clean.strip())
        except json.JSONDecodeError:
            result = {"verdict": "ERROR", "confidence": 0, "reasoning": result_text[:100]}
        self.verdicts[claim[:40]] = result
        return result
