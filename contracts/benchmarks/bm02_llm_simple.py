# contracts/benchmarks/bm02_llm_simple.py
from genlayer import IContract, public

class BM02LLMSimple(IContract):
    """
    Benchmark 02: Simple LLM call.
    Short prompt, deterministic expected output.
    Measures baseline LLM latency and consensus time.
    """

    def __init__(self):
        self.results: list = []

    @public
    def classify_sentiment(self, text: str) -> str:
        prompt = f"""
Classify the sentiment of this text as exactly one word: POSITIVE, NEGATIVE, or NEUTRAL.
Text: "{text}"
Respond with only the single word classification.
EQUIVALENCE NOTE: Only the classification word matters.
Formatting differences are not significant.
"""
        result = call_llm(prompt)
        self.results.append({"text": text[:50], "sentiment": result.strip()})
        return result.strip()
