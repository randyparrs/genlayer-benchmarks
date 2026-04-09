# { "Depends": "py-genlayer:test" }
# BM-04: Web Fetch Without LLM
# Measures native web access latency across validators.
# Each validator independently fetches the URL.
# Equivalence Principle: content length within ±500 chars 

import json
from genlayer import *


class BM04WebFetch(gl.Contract):
    fetched: DynArray[str]

    def __init__(self):
        pass

    @gl.public.write
    def fetch_and_measure(self, url: str) -> str:
        def leader_fn():
            response = gl.nondet.web.get(url)
            content = response.body.decode("utf-8")
            content_length = len(content)
            first_100 = content[:100].replace("\n", " ")
            return json.dumps({
                "url": url,
                "content_length": content_length,
                "preview": first_100
            }, sort_keys=True)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_raw = leader_fn()
                leader_data = json.loads(leader_result.calldata)
                validator_data = json.loads(validator_raw)
                return abs(leader_data["content_length"] - validator_data["content_length"]) <= 500
            except Exception:
                return False

        raw = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        self.fetched.append(url[:80])
        return raw

    @gl.public.view
    def get_count(self) -> u256:
        return u256(len(self.fetched))
