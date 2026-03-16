# contracts/benchmarks/bm03_llm_complex.py
from genlayer import IContract, public
import json

class BM03LLMComplex(IContract):
    """
    Benchmark 03: Complex LLM call with structured output.
    Long prompt, JSON response required.
    Measures how prompt complexity affects latency and consensus reliability.
    """

    def __init__(self):
        self.analyses: dict[str, dict] = {}

    @public
    def analyze_topic(self, topic: str) -> dict:
        prompt = f"""
Analyze the following topic and respond ONLY with a valid JSON object.
Topic: "{topic}"
JSON format:
{{
  "summary": "<2 sentence summary>",
  "pros": ["<pro 1>", "<pro 2>", "<pro 3>"],
  "cons": ["<con 1>", "<con 2>", "<con 3>"],
  "verdict": "<one word: POSITIVE, NEGATIVE, or NEUTRAL>",
  "confidence": <integer 0-100>
}}
EQUIVALENCE NOTE: Two responses are equivalent if they have the same verdict
and confidence within 10 points. Summary and pros/cons wording may differ.
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
            result = {"error": "Failed to parse JSON", "raw": result_text[:100]}
        self.analyses[topic[:30]] = result
        return result
