# { "Depends": "py-genlayer:test" }

import json
from genlayer import *
from dataclasses import dataclass


@allow_storage
@dataclass
class BenchmarkResult:
    id: u256
    category: str
    input_data: str
    output_data: str
    consensus_reached: bool
    confidence: u256


class GenLayerBenchmark(gl.Contract):

    owner: Address
    results: DynArray[BenchmarkResult]
    result_count: u256
    bm01_runs: u256
    bm02_runs: u256
    bm03_runs: u256
    bm04_runs: u256
    bm05_runs: u256
    total_consensus: u256

    def __init__(self, owner_address: str):
        self.owner = Address(owner_address)
        self.result_count = u256(0)
        self.bm01_runs = u256(0)
        self.bm02_runs = u256(0)
        self.bm03_runs = u256(0)
        self.bm04_runs = u256(0)
        self.bm05_runs = u256(0)
        self.total_consensus = u256(0)

    @gl.public.view
    def get_benchmark_summary(self) -> str:
        total = int(self.result_count)
        consensus = int(self.total_consensus)
        rate = int((consensus / total) * 100) if total > 0 else 0
        return (
            f"GenLayer Benchmark Suite\n"
            f"Total Runs: {total}\n"
            f"BM-01 Deterministic: {int(self.bm01_runs)} runs\n"
            f"BM-02 LLM Simple:    {int(self.bm02_runs)} runs\n"
            f"BM-03 LLM Complex:   {int(self.bm03_runs)} runs\n"
            f"BM-04 Web Only:      {int(self.bm04_runs)} runs\n"
            f"BM-05 Full Intel:    {int(self.bm05_runs)} runs\n"
            f"Consensus Rate:      {rate}%"
        )

    @gl.public.view
    def get_result(self, result_id: u256) -> str:
        idx = int(result_id)
        if idx >= len(self.results):
            return "Result not found"
        r = self.results[idx]
        return (
            f"ID: {int(r.id)} | "
            f"Category: {r.category} | "
            f"Input: {r.input_data} | "
            f"Output: {r.output_data} | "
            f"Consensus: {r.consensus_reached} | "
            f"Confidence: {int(r.confidence)}%"
        )

    @gl.public.view
    def get_result_count(self) -> u256:
        return self.result_count

    @gl.public.write
    def bm01_deterministic(self, key: str, value: str) -> str:
        output = f"stored:{key}={value}"
        rid = self.result_count

        self.results.append(BenchmarkResult(
            id=rid,
            category="BM-01",
            input_data=f"{key}={value}",
            output_data=output,
            consensus_reached=True,
            confidence=u256(100),
        ))
        self.result_count = u256(int(rid) + 1)
        self.bm01_runs = u256(int(self.bm01_runs) + 1)
        self.total_consensus = u256(int(self.total_consensus) + 1)
        return output

    @gl.public.write
    def bm02_llm_simple(self, text: str) -> str:
        def leader_fn():
            prompt = f"""Classify the sentiment of this text.
Text: "{text}"
Respond ONLY with one word: POSITIVE, NEGATIVE, or NEUTRAL.
No other text."""
            result = gl.nondet.exec_prompt(prompt)
            sentiment = result.strip().upper()
            if sentiment not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
                sentiment = "NEUTRAL"
            return sentiment

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                validator_out = leader_fn()
                return leader_result.calldata.strip() == validator_out.strip()
            except Exception:
                return False

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        rid = self.result_count

        self.results.append(BenchmarkResult(
            id=rid,
            category="BM-02",
            input_data=text[:50],
            output_data=result,
            consensus_reached=True,
            confidence=u256(95),
        ))
        self.result_count = u256(int(rid) + 1)
        self.bm02_runs = u256(int(self.bm02_runs) + 1)
        self.total_consensus = u256(int(self.total_consensus) + 1)
        return result

    @gl.public.write
    def bm03_llm_complex(self, topic: str) -> str:
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
        data = json.loads(raw)
        output = f"{data['verdict']} ({data['confidence']}%)"
        rid = self.result_count

        self.results.append(BenchmarkResult(
            id=rid,
            category="BM-03",
            input_data=topic[:50],
            output_data=output,
            consensus_reached=True,
            confidence=u256(data["confidence"]),
        ))
        self.result_count = u256(int(rid) + 1)
        self.bm03_runs = u256(int(self.bm03_runs) + 1)
        self.total_consensus = u256(int(self.total_consensus) + 1)
        return raw

    @gl.public.write
    def bm04_web_fetch(self, url: str) -> str:
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
        data = json.loads(raw)
        output = f"length:{data['content_length']} preview:{data['preview'][:50]}"
        rid = self.result_count

        self.results.append(BenchmarkResult(
            id=rid,
            category="BM-04",
            input_data=url[:80],
            output_data=output[:100],
            consensus_reached=True,
            confidence=u256(100),
        ))
        self.result_count = u256(int(rid) + 1)
        self.bm04_runs = u256(int(self.bm04_runs) + 1)
        self.total_consensus = u256(int(self.total_consensus) + 1)
        return raw

    @gl.public.write
    def bm05_full_intelligent(self, claim: str, source_url: str) -> str:
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
        output = f"{data['verdict']} ({data['confidence']}%) {data['reasoning']}"
        rid = self.result_count

        self.results.append(BenchmarkResult(
            id=rid,
            category="BM-05",
            input_data=claim[:50],
            output_data=output[:150],
            consensus_reached=True,
            confidence=u256(data["confidence"]),
        ))
        self.result_count = u256(int(rid) + 1)
        self.bm05_runs = u256(int(self.bm05_runs) + 1)
        self.total_consensus = u256(int(self.total_consensus) + 1)
        return raw
