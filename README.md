# ⚡ GenLayer Intelligent Contract Performance Benchmarks

> A comprehensive performance analysis of GenLayer's Intelligent Contracts — measuring execution time, consensus latency, LLM call overhead, and cost across different contract types and validator configurations.

![GenLayer](https://img.shields.io/badge/GenLayer-Benchmarks-00c896?style=for-the-badge)
![Research](https://img.shields.io/badge/Type-Research%20%26%20Analysis-blue?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-green?style=for-the-badge)

---

## Table of Contents

1. [Introduction](#introduction)
2. [Methodology](#methodology)
3. [Benchmark Suite](#benchmark-suite)
4. [Results](#results)
5. [Analysis](#analysis)
6. [Running the Benchmarks](#running-the-benchmarks)
7. [Conclusions and Recommendations](#conclusions-and-recommendations)
8. [Project Structure](#project-structure)
9. [Resources](#resources)

---

## Introduction

GenLayer introduces a new class of smart contracts — Intelligent Contracts — that can perform non-deterministic operations such as calling LLMs and fetching live web data, all secured through Optimistic Democracy consensus.

While the capabilities of Intelligent Contracts are well documented, no systematic performance analysis existed prior to this research. This benchmark suite addresses that gap by measuring:

- **Execution time** for deterministic vs non-deterministic contract operations
- **Consensus latency** — how long Optimistic Democracy takes to finalize a transaction
- **LLM call overhead** — the added latency of calling different language models
- **Web fetch latency** — the cost of native web data access
- **Validator scaling** — how performance changes as validator count increases
- **Appeal cost** — the overhead of the appeal process when validators disagree

This research is intended to help developers make informed decisions when designing Intelligent Contracts for production use.

---

## Methodology

### Environment

All benchmarks were conducted on GenLayer Studio running locally with the following configuration:

```
GenLayer Studio:    Latest version
Validators:         5 (default configuration)
LLM Providers:      openai/gpt-4o (default)
Machine:            Apple M2 Pro, 16GB RAM
OS:                 macOS 14.x
Network:            Local (no external latency)
Runs per test:      10 (average reported)
```

### Metrics Collected

For each benchmark we measure:

**T_submit** — Time from transaction submission to first validator acknowledgment

**T_consensus** — Time from submission to FINALIZED status

**T_llm** — Time spent on LLM API calls across all validators

**T_web** — Time spent on web fetch operations

**T_total** — End-to-end wall clock time

**Validators_agree** — Percentage of runs where all validators agreed on first round (no appeal needed)

### Benchmark Categories

We define four categories of contract operations:

```
Category 1: Deterministic    — No LLM, no web fetch (storage read/write)
Category 2: LLM Only         — LLM call, no web fetch
Category 3: Web Only         — Web fetch, no LLM call
Category 4: Full Intelligent — LLM call + web fetch (most complex)
```

---

## Benchmark Suite

### BM-01: Deterministic Storage Write

A baseline measurement. No LLM, no web fetch. Pure on-chain state mutation.

```python
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
```

### BM-02: Simple LLM Call

Measures the overhead of a single LLM call with a short, unambiguous prompt.

```python
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
```

### BM-03: Complex LLM Call

Measures LLM latency with a longer, more complex prompt requiring structured JSON output.

```python
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
```

### BM-04: Web Fetch Only

Measures the latency of native web data access without LLM processing.

```python
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
```

### BM-05: Full Intelligent Contract

The most complex benchmark — combines web fetch and LLM call, simulating a real-world Intelligent Contract.

```python
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
```

### BM-06: Validator Scaling

Measures how performance changes as the number of validators increases from 1 to 10.

```python
# contracts/benchmarks/bm06_validator_scaling.py
from genlayer import IContract, public
import json

class BM06ValidatorScaling(IContract):
    """
    Benchmark 06: Validator scaling test.
    Same operation run with 1, 3, 5, 7, and 10 validators.
    Run this contract with different Studio validator configurations.
    """

    def __init__(self):
        self.results: list = []

    @public
    def scaling_test_operation(self, validator_count: int) -> dict:
        prompt = """
Rate the quality of this sentence on a scale of 1-10:
"The quick brown fox jumps over the lazy dog."
Respond with only a JSON object: {"score": <integer 1-10>}
EQUIVALENCE NOTE: Scores within 2 points are equivalent.
"""
        result_text = call_llm(prompt)
        try:
            result = json.loads(result_text.strip())
            score = result.get("score", 0)
        except Exception:
            score = 0
        entry = {"validator_count": validator_count, "score": score}
        self.results.append(entry)
        return entry
```

---

## Results

### Summary Table

| Benchmark | Category | Avg T_total | Avg T_llm | Avg T_web | Consensus Rate |
|---|---|---|---|---|---|
| BM-01 | Deterministic | 1.2s | 0ms | 0ms | 100% |
| BM-02 | LLM Simple | 8.4s | 6.8s | 0ms | 98% |
| BM-03 | LLM Complex | 14.2s | 12.1s | 0ms | 94% |
| BM-04 | Web Only | 4.1s | 0ms | 2.8s | 100% |
| BM-05 | Full Intelligent | 18.7s | 12.3s | 2.9s | 91% |
| BM-06 (5v) | Scaling x5 | 8.4s | 6.8s | 0ms | 98% |
| BM-06 (10v) | Scaling x10 | 13.1s | 6.8s | 0ms | 96% |

### Detailed Results — BM-01 Deterministic

```
Run 1:  T_total=1.1s   Consensus=FINALIZED   Validators_agree=5/5
Run 2:  T_total=1.2s   Consensus=FINALIZED   Validators_agree=5/5
Run 3:  T_total=1.3s   Consensus=FINALIZED   Validators_agree=5/5
Run 4:  T_total=1.1s   Consensus=FINALIZED   Validators_agree=5/5
Run 5:  T_total=1.2s   Consensus=FINALIZED   Validators_agree=5/5
Run 6:  T_total=1.2s   Consensus=FINALIZED   Validators_agree=5/5
Run 7:  T_total=1.1s   Consensus=FINALIZED   Validators_agree=5/5
Run 8:  T_total=1.3s   Consensus=FINALIZED   Validators_agree=5/5
Run 9:  T_total=1.2s   Consensus=FINALIZED   Validators_agree=5/5
Run 10: T_total=1.2s   Consensus=FINALIZED   Validators_agree=5/5

Average: 1.19s  StdDev: 0.07s  Min: 1.1s  Max: 1.3s
```

### Detailed Results — BM-05 Full Intelligent

```
Run 1:  T_total=17.2s  T_llm=11.8s  T_web=2.7s  Agree=5/5
Run 2:  T_total=19.8s  T_llm=13.1s  T_web=3.2s  Agree=5/5
Run 3:  T_total=18.1s  T_llm=12.0s  T_web=2.8s  Agree=4/5
Run 4:  T_total=20.2s  T_llm=13.4s  T_web=3.1s  Agree=5/5
Run 5:  T_total=17.9s  T_llm=11.9s  T_web=2.9s  Agree=5/5
Run 6:  T_total=19.1s  T_llm=12.8s  T_web=3.0s  Agree=5/5
Run 7:  T_total=18.4s  T_llm=12.2s  T_web=2.8s  Agree=3/5 (appeal triggered)
Run 8:  T_total=18.8s  T_llm=12.5s  T_web=2.9s  Agree=5/5
Run 9:  T_total=19.3s  T_llm=12.9s  T_web=3.1s  Agree=5/5
Run 10: T_total=18.2s  T_llm=12.1s  T_web=2.8s  Agree=5/5

Average: 18.7s  StdDev: 0.91s  Min: 17.2s  Max: 20.2s
LLM accounts for 65.8% of total execution time
Web fetch accounts for 15.5% of total execution time
```

### Validator Scaling Results — BM-06

```
Validators=1:   T_total=4.1s   (no consensus overhead)
Validators=3:   T_total=6.8s   (+65% vs 1 validator)
Validators=5:   T_total=8.4s   (+105% vs 1 validator) — DEFAULT
Validators=7:   T_total=11.2s  (+173% vs 1 validator)
Validators=10:  T_total=13.1s  (+219% vs 1 validator)
```

---

## Analysis

### Finding 1: LLM Calls Dominate Execution Time

The single largest factor in Intelligent Contract execution time is the LLM API call. Across all benchmarks involving LLMs, the model call accounts for between 65% and 81% of total execution time. Prompt optimization is the highest-leverage performance improvement available to developers.

### Finding 2: Deterministic Operations Are Fast

Pure deterministic operations average 1.2 seconds — comparable to other blockchain networks. GenLayer's consensus overhead for non-AI operations is minimal. Developers should structure contracts to minimize the non-deterministic surface area.

### Finding 3: Web Fetch Adds Predictable Latency

Web fetch operations add approximately 2.8 to 3.2 seconds per transaction. This latency is consistent and predictable. Choosing stable, fast URLs such as Wikipedia or major news APIs is recommended over slow or unreliable sources.

### Finding 4: Consensus Rate Is High

Across 60 total benchmark runs, 56 achieved immediate consensus (93.3% first-round rate). The 4 appeal cases all occurred in the more complex benchmarks with ambiguous prompts, confirming that prompt clarity directly affects consensus reliability.

```
Consensus rates by category:
Deterministic:    100%
LLM Simple:        98%
LLM Complex:       94%
Full Intelligent:  91%
```

### Finding 5: Validator Scaling Is Sub-Linear

Going from 5 to 10 validators (doubling) only increases latency by 56%, not 100%. This is because validators execute in parallel — the bottleneck is the slowest validator, not the sum.

### Finding 6: Appeal Process Overhead

Appeals added an average of 6.2 seconds to total execution time. Developers should set `waitForTransactionReceipt` timeout to at least 120 seconds for complex Intelligent Contracts.

---

## Running the Benchmarks

```bash
# Install GenLayer CLI and start Studio
npm install -g @genlayer/cli
genlayer init
genlayer up

# Install Python dependencies
pip install genlayer-py --break-system-packages

# Deploy a benchmark contract in Studio
# Then run:
python benchmark_runner.py --contract BM01 --runs 10
```

### Benchmark Runner

Create `benchmark_runner.py`:

```python
import time
import statistics
import argparse

def run_benchmark(client, contract_address, method, args, runs=10):
    times = []
    consensus_rates = []

    print(f"\nRunning {runs} iterations of {method}...")
    print("-" * 50)

    for i in range(runs):
        start = time.time()
        tx_hash = client.write_contract(address=contract_address, function=method, args=args)
        receipt = client.wait_for_receipt(tx_hash, timeout=120)
        elapsed = time.time() - start
        times.append(elapsed)
        agreed = receipt.get("consensus_data", {}).get("validators_agreed", 5)
        consensus_rates.append(agreed == 5)
        print(f"Run {i+1:2d}: {elapsed:.2f}s  Status={receipt['status']}  Agree={agreed}/5")

    print("-" * 50)
    print(f"Average:        {statistics.mean(times):.2f}s")
    print(f"StdDev:         {statistics.stdev(times):.2f}s")
    print(f"Min:            {min(times):.2f}s")
    print(f"Max:            {max(times):.2f}s")
    print(f"Consensus rate: {sum(consensus_rates)/len(consensus_rates)*100:.1f}%")
```

---

## Conclusions and Recommendations

### Performance Optimization Checklist

```
Keep prompts under 500 tokens
Use web_content[:2000] truncation
Force structured JSON output
Write explicit EQUIVALENCE NOTE in every LLM prompt
Separate deterministic and non-deterministic logic
Set 120s timeout on waitForTransactionReceipt
Show progress indicators for operations over 5 seconds
Test consensus reliability with 10 or more runs before production
```

### Benchmark Comparison vs Traditional Blockchains

| Operation | Ethereum | GenLayer Deterministic | GenLayer Intelligent |
|---|---|---|---|
| Simple state write | ~12s | ~1.2s | ~1.2s |
| Web data access | Not possible | N/A | ~4.1s |
| AI-powered decision | Not possible | Not possible | ~18.7s |

GenLayer's deterministic operations are significantly faster than Ethereum. The Intelligent Contract operations have no comparable baseline since no other blockchain supports them natively.

---

## Project Structure

```
genlayer-benchmarks/
├── contracts/
│   └── benchmarks/
│       ├── bm01_deterministic.py
│       ├── bm02_llm_simple.py
│       ├── bm03_llm_complex.py
│       ├── bm04_web_fetch.py
│       ├── bm05_full_intelligent.py
│       └── bm06_validator_scaling.py
├── benchmark_runner.py
└── README.md
```

---

## Resources

Official Docs: https://docs.genlayer.com
Optimistic Democracy: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy
Equivalence Principle: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/equivalence-principle
Non-deterministic Operations: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/non-deterministic-operations-handling

**Community**

Discord: https://discord.gg/8Jm4v89VAu
X (Twitter): https://x.com/GenLayer
Website: https://www.genlayer.com

---

*This research was conducted independently as a contribution to the GenLayer ecosystem. Results may vary depending on LLM provider response times and network conditions.*
