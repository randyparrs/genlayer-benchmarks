# contracts/benchmarks/bm04_web_fetch.py
from genlayer import IContract, public

class BM04WebFetch(IContract):
    """
    Benchmark 04: Web fetch without LLM.
    Measures native web access latency across validators.
    Each validator independently fetches the URL.
    """

    def __init__(self):
        self.fetched: dict[str, int] = {}

    @public
    def fetch_and_measure(self, url: str) -> dict:
        content = get_webpage(url, mode="text")
        result = {
            "url": url,
            "content_length": len(content),
            "first_100_chars": content[:100],
        }
        self.fetched[url] = len(content)
        return result
