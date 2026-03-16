# contracts/benchmarks/bm01_deterministic.py
from genlayer import IContract, public

class BM01Deterministic(IContract):
    """
    Benchmark 01: Deterministic storage write.
    Baseline — no LLM, no web fetch.
    Measures pure consensus overhead on simple state changes.
    """

    def __init__(self):
        self.counter: int = 0
        self.data: dict[str, int] = {}

    @public
    def increment(self) -> int:
        self.counter += 1
        return self.counter

    @public
    def store_value(self, key: str, value: int) -> str:
        self.data[key] = value
        return f"Stored {key}={value}"

    @public
    def get_counter(self) -> int:
        return self.counter
