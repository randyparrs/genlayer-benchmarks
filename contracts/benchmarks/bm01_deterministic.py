# { "Depends": "py-genlayer:test" }
# BM-01: Deterministic Storage Write
# Baseline — no LLM, no web fetch.
# Measures pure consensus overhead on simple state changes.

from genlayer import *


class BM01Deterministic(gl.Contract):
    counter: u256
    last_key: str
    last_value: str

    def __init__(self):
        self.counter = u256(0)
        self.last_key = ""
        self.last_value = ""

    @gl.public.write
    def increment(self) -> u256:
        self.counter = u256(int(self.counter) + 1)
        return self.counter

    @gl.public.write
    def store_value(self, key: str, value: str) -> str:
        self.last_key = key
        self.last_value = value
        return f"Stored {key}={value}"

    @gl.public.view
    def get_counter(self) -> u256:
        return self.counter

    @gl.public.view
    def get_last(self) -> str:
        return f"{self.last_key}={self.last_value}"
