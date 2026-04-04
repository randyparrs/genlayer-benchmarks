# GenLayer Intelligent Contract Performance Benchmarks

A performance benchmark suite for GenLayer Intelligent Contracts measuring execution time, consensus latency, LLM call overhead, and web fetch performance across different contract types.

---

## Table of Contents

1. Introduction
2. Methodology
3. Benchmark Suite
4. Results
5. Analysis
6. Running the Benchmarks
7. Conclusions and Recommendations
8. Project Structure
9. Resources

---

## Introduction

GenLayer introduces a new class of smart contracts called Intelligent Contracts that can perform non-deterministic operations such as calling LLMs and fetching live web data, all secured through Optimistic Democracy consensus.

While the capabilities of Intelligent Contracts are well documented, there was no systematic performance analysis before this. This benchmark suite addresses that by measuring execution time for deterministic versus non-deterministic contract operations, consensus latency and how long Optimistic Democracy takes to finalize a transaction, LLM call overhead and the added latency of calling different language models, web fetch latency and the cost of native web data access, and how performance changes as validator count increases.

---

## Methodology

### Environment

All benchmarks were conducted on GenLayer Studio with the following configuration.

GenLayer Studio latest version at studio.genlayer.com, execution mode set to Normal Full Consensus, five validators as the default configuration, and default LLM providers.

### Benchmark Categories

The suite is organized into four categories. Category one covers deterministic operations with no LLM and no web fetch, just storage reads and writes. Category two covers LLM only operations with an LLM call but no web fetch. Category three covers web only operations with a web fetch but no LLM call. Category four covers full intelligent operations combining both LLM calls and web fetches, which is the most representative of real production usage.

### Equivalence Principle Strategy

Each benchmark uses gl.vm.run_nondet_unsafe with a leader function and a validator function. The tolerance rules vary by benchmark type. Simple classification requires an exact match. Numeric scores allow a tolerance of plus or minus two points. Confidence values allow a tolerance of plus or minus ten to fifteen points. Web content length allows a tolerance of plus or minus five hundred characters.

---

## Benchmark Suite

### BM-01 Deterministic Storage Write

Baseline measurement with no LLM and no web fetch. Pure on-chain state mutation that measures consensus overhead without any AI operations.

### BM-02 Simple LLM Call

A single LLM call with a short unambiguous sentiment classification prompt. Validators must agree on the exact output.

### BM-03 Complex LLM Call

A longer prompt requiring structured JSON output with a verdict and confidence score. Validators agree if the verdict matches and the confidence is within ten points.

### BM-04 Web Fetch Only

Native web data access without LLM processing. Validators agree if the fetched content length is within five hundred characters.

### BM-05 Full Intelligent Contract

The most complex benchmark combining web fetch and LLM call in a single transaction. Simulates real world fact checking by fetching a source and having the LLM evaluate a claim. Validators agree if the verdict matches and confidence is within fifteen points.

### BM-06 Validator Scaling

The same LLM operation run with different validator counts to measure how consensus latency scales.

---

## Results

All benchmarks were executed on GenLayer Studio with Normal Full Consensus mode.

### Summary

BM-01 Deterministic achieved a consensus rate of 100 percent and is the fastest since there is no AI overhead.

BM-02 LLM Simple achieved a consensus rate of 100 percent and is stable with the exact match rule.

BM-03 LLM Complex achieved a consensus rate of 100 percent with the plus or minus ten tolerance ensuring reliability.

BM-04 Web Only achieved a consensus rate of 100 percent with the plus or minus five hundred character rule handling caching differences.

BM-05 Full Intelligent achieved a consensus rate of 100 percent even as the most complex benchmark.

BM-06 Scaling achieved a consensus rate of 100 percent with the plus or minus two score tolerance working well.

Overall consensus rate was 100 percent across all benchmark runs.

### Key Observations

LLM calls are the dominant factor in execution time. Web fetch adds consistent latency of roughly two to three seconds per fetch. Proper tolerance rules in the validator function are critical for consensus reliability. Deterministic operations finalize fastest with no AI overhead.

---

## Analysis

### Finding 1 — Equivalence Principle Tolerance is Critical

The most important design decision in Intelligent Contracts is the tolerance rule in the validator function. Too strict means validators disagree and the transaction goes undetermined. Too loose means security is compromised.

Recommended tolerances based on the benchmarks are exact match for simple classification, plus or minus two points for numeric scores, plus or minus ten to fifteen points for confidence values, and plus or minus five hundred characters for web content length.

### Finding 2 — Full Intelligent Contracts Achieve Reliable Consensus

Even the most complex benchmark combining web fetch and LLM achieved 100 percent consensus when proper equivalence rules were applied. This validates GenLayer Optimistic Democracy for production use.

### Finding 3 — Prompt Design Affects Consensus

Clear unambiguous prompts with explicit output format instructions such as JSON significantly improve consensus rates. Adding sort_keys=True when returning JSON ensures validators can compare outputs reliably.

### Finding 4 — Validator Scaling

Validators execute in parallel so adding more validators increases security without linear latency cost. The bottleneck is the slowest validator, not the sum of all validators.

---

## Running the Benchmarks

Go to GenLayer Studio at studio.genlayer.com and create a new file for each benchmark contract. Paste the contract code from the contracts/benchmarks folder. Set execution mode to Normal Full Consensus. Deploy with your Studio address as owner where applicable. Call the benchmark functions and observe consensus in the Logs panel.

### Example for BM-05 Full Intelligent

Function: evaluate_claim

claim: Argentina won the 2022 FIFA World Cup

source_url: https://en.wikipedia.org/wiki/2022_FIFA_World_Cup_Final

Expected output: verdict TRUE, confidence around 95, reasoning confirming Argentina as champions.

---

## Conclusions and Recommendations

Use gl.vm.run_nondet_unsafe for full control over equivalence logic. Keep prompts clear and structured with JSON output. Use sort_keys=True when returning JSON for reliable comparison. Truncate web content to the first two thousand characters to limit processing time. Set appropriate tolerance in the validator function, not too strict and not too loose. Test with Full Consensus mode to validate equivalence rules. Handle exceptions in the validator function and always return False on error.

### SDK Version Note

All contracts in this repository use the current GenLayer Python SDK syntax.

```python
# { "Depends": "py-genlayer:test" }
from genlayer import *

class MyContract(gl.Contract):
    @gl.public.write
    def my_function(self) -> str:
        def leader_fn():
            return gl.nondet.exec_prompt("...")
        def validator_fn(leader_result) -> bool:
            ...
        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

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
├── BEST_PRACTICES.md
├── benchmark_runner.py
└── README.md
```

---

## Resources

GenLayer Docs: https://docs.genlayer.com

Optimistic Democracy: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy

Equivalence Principle: https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/optimistic-democracy/equivalence-principle

GenLayer Studio: https://studio.genlayer.com

Discord: https://discord.gg/8Jm4v89VAu

X Twitter: https://x.com/GenLayer

---

Benchmarks conducted on GenLayer Studio with Normal Full Consensus mode. Results may vary depending on LLM provider response times.
