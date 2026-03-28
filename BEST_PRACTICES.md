# 📚 GenLayer Intelligent Contract — Best Practices Guide

> A practical guide for developers building Intelligent Contracts on GenLayer. Based on empirical testing across multiple contract types achieving 100% consensus rate.

---

## Table of Contents

1. [Contract Structure](#1-contract-structure)
2. [Equivalence Principle Patterns](#2-equivalence-principle-patterns)
3. [Prompt Engineering for Consensus](#3-prompt-engineering-for-consensus)
4. [Web Fetch Best Practices](#4-web-fetch-best-practices)
5. [Storage Patterns](#5-storage-patterns)
6. [Common Errors and Fixes](#6-common-errors-and-fixes)
7. [Tolerance Reference Table](#7-tolerance-reference-table)
8. [Quick Checklist](#8-quick-checklist)

---

## 1. Contract Structure

### ✅ Correct — Minimal Contract Template

```python
# { "Depends": "py-genlayer:test" }

import json
from genlayer import *

class MyContract(gl.Contract):

    # Declare all state variables at class level
    owner: str
    counter: u256
    items: DynArray[str]

    def __init__(self, owner_address: str):
        self.owner = owner_address
        self.counter = u256(0)

    @gl.public.view
    def get_data(self) -> str:
        return f"Counter: {int(self.counter)}"

    @gl.public.write
    def do_something(self, input: str) -> str:
        self.counter = u256(int(self.counter) + 1)
        return f"Done: {input}"
```

### ❌ Common Mistakes

```python
# WRONG — old syntax, does not work in GenLayer Studio
from genlayer import IContract, public

class MyContract(IContract):
    @public
    def my_function(self) -> str:
        result = call_llm("prompt")        # ❌ old API
        data = get_webpage(url, mode="text") # ❌ old API

# CORRECT — current syntax
from genlayer import *

class MyContract(gl.Contract):
    @gl.public.write
    def my_function(self) -> str:
        result = gl.nondet.exec_prompt("prompt")      # ✅
        response = gl.nondet.web.get(url)             # ✅
        data = response.body.decode("utf-8")          # ✅
```

---

## 2. Equivalence Principle Patterns

The Equivalence Principle is how GenLayer achieves consensus on non-deterministic operations. Always use `gl.vm.run_nondet_unsafe` with a `leader_fn` and `validator_fn`.

### Pattern 1 — Exact Match (Simple Classification)

Use when output is a fixed set of values (e.g., YES/NO, POSITIVE/NEGATIVE).

```python
def leader_fn():
    result = gl.nondet.exec_prompt("Classify as POSITIVE or NEGATIVE: ...")
    return result.strip().upper()

def validator_fn(leader_result) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    validator_out = leader_fn()
    return leader_result.calldata.strip() == validator_out.strip()  # exact match

result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

### Pattern 2 — Numeric Tolerance (Scores, Prices)

Use when output is numeric and may vary slightly between validators.

```python
def validator_fn(leader_result) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    validator_raw = leader_fn()
    leader_data = json.loads(leader_result.calldata)
    validator_data = json.loads(validator_raw)
    # Allow ±10 points difference
    return abs(leader_data["score"] - validator_data["score"]) <= 10
```

### Pattern 3 — Field Matching (Structured JSON)

Use when output has multiple fields but only key fields matter for consensus.

```python
def validator_fn(leader_result) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    validator_raw = leader_fn()
    leader_data = json.loads(leader_result.calldata)
    validator_data = json.loads(validator_raw)
    # Only compare the decision field — reasoning may differ
    return leader_data["verdict"] == validator_data["verdict"]
```

### Pattern 4 — Web Fetch + LLM (Full Intelligent)

The most common production pattern — fetch data then analyze.

```python
def leader_fn():
    response = gl.nondet.web.get(url)
    web_data = response.body.decode("utf-8")[:2000]  # always truncate!
    result = gl.nondet.exec_prompt(f"Analyze: {web_data}")
    data = json.loads(result.strip().replace("```json","").replace("```",""))
    return json.dumps(data, sort_keys=True)  # sort_keys for reliable comparison!

def validator_fn(leader_result) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    try:
        validator_raw = leader_fn()
        leader_data = json.loads(leader_result.calldata)
        validator_data = json.loads(validator_raw)
        if leader_data["outcome"] != validator_data["outcome"]:
            return False
        return abs(leader_data["confidence"] - validator_data["confidence"]) <= 15
    except Exception:
        return False  # always return False on error, never True

result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

---

## 3. Prompt Engineering for Consensus

Good prompts are critical for reliable consensus. Follow these rules:

### ✅ DO — Structure Your Prompts for Determinism

```python
prompt = f"""Analyze this topic and respond ONLY with a JSON object.
Topic: "{topic}"

{{"verdict": "POSITIVE", "confidence": 80, "reasoning": "one sentence"}}

Rules:
- verdict: exactly POSITIVE, NEGATIVE, or NEUTRAL
- confidence: integer 0-100
- reasoning: one sentence max
No extra text."""
```

### ✅ DO — Use sort_keys=True When Returning JSON

```python
# Ensures consistent key ordering across validators
return json.dumps({"verdict": verdict, "confidence": conf}, sort_keys=True)
```

### ✅ DO — Strip Markdown Fences

```python
# LLMs sometimes wrap JSON in markdown code blocks
clean = result.strip().replace("```json", "").replace("```", "").strip()
data = json.loads(clean)
```

### ✅ DO — Validate and Clamp Output Values

```python
verdict = data.get("verdict", "NEUTRAL")
if verdict not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
    verdict = "NEUTRAL"  # safe default

confidence = int(data.get("confidence", 50))
confidence = max(0, min(100, confidence))  # clamp to valid range
```

### ❌ DON'T — Ask for Open-Ended Text Without Structure

```python
# BAD — two validators will get completely different text
result = gl.nondet.exec_prompt("Tell me about Bitcoin")

# GOOD — structured output with clear equivalence rules
result = gl.nondet.exec_prompt("""Analyze Bitcoin. Respond ONLY with JSON:
{"verdict": "POSITIVE", "confidence": 80}""")
```

### ❌ DON'T — Return Raw LLM Text

```python
# BAD — tiny wording differences cause validator disagreement
return gl.nondet.exec_prompt(prompt)

# GOOD — normalize before returning
raw = gl.nondet.exec_prompt(prompt)
data = json.loads(raw.strip())
return json.dumps({"verdict": data["verdict"]}, sort_keys=True)
```

---

## 4. Web Fetch Best Practices

### ✅ Always Truncate Web Content

```python
response = gl.nondet.web.get(url)
content = response.body.decode("utf-8")[:2000]  # limit to 2000 chars
```

Web pages can be very large. Truncating:
- Reduces LLM processing time
- Keeps content within prompt limits
- Improves consistency across validators

### ✅ Use Reliable, Stable URLs

| ✅ Good Sources | ❌ Avoid |
|----------------|---------|
| Wikipedia | Dynamic JS-rendered pages |
| Official news APIs | Pages requiring login |
| Government sites | Sites with aggressive caching |
| CoinGecko API | Sites that block scraping |

### ✅ Handle Fetch Errors Gracefully

```python
def leader_fn():
    try:
        response = gl.nondet.web.get(url)
        web_data = response.body.decode("utf-8")[:2000]
    except Exception:
        web_data = "No data available."  # fallback, don't crash
    ...
```

### ✅ Use Wikipedia for Factual Queries

```python
# Wikipedia is reliable, scrapeable, and consistent across validators
url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
```

---

## 5. Storage Patterns

### ✅ Use DynArray[str] for Flexible Storage

When you need key-value storage without complex types:

```python
class MyContract(gl.Contract):
    data: DynArray[str]  # stores "key:value" pairs

def _get(self, key: str) -> str:
    prefix = f"{key}:"
    for i in range(len(self.data)):
        if self.data[i].startswith(prefix):
            return self.data[i][len(prefix):]
    return ""

def _set(self, key: str, value: str) -> None:
    prefix = f"{key}:"
    for i in range(len(self.data)):
        if self.data[i].startswith(prefix):
            self.data[i] = f"{prefix}{value}"
            return
    self.data.append(f"{prefix}{value}")
```

### ✅ Always Initialize u256 Correctly

```python
# CORRECT
self.counter = u256(0)
self.counter = u256(int(self.counter) + 1)  # increment

# WRONG
self.counter = 0        # plain int won't work
self.counter += 1       # won't work with u256
```

### ✅ Avoid External Dataclasses for Constructor Args

```python
# This causes "Could not load contract schema" error in Studio
@allow_storage
@dataclass
class MyData:
    field: str

class MyContract(gl.Contract):
    def __init__(self, data: MyData):  # ❌ Studio can't parse this
        ...

# CORRECT — use primitive types in constructor
class MyContract(gl.Contract):
    def __init__(self, owner_address: str, name: str):  # ✅
        ...
```

---

## 6. Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Could not load contract schema` | Complex constructor args or old syntax | Use primitive types (`str`, `u256`, `bool`) in constructor |
| `FINALIZED / ERROR` | Assert failed or wrong state | Check function preconditions and state |
| Validator disagreement | Tolerance too strict | Increase tolerance in `validator_fn` |
| JSON parse error | LLM returned markdown | Add `.replace("```json","").replace("```","")` |
| `gl.eq_principle_prompt_comparative` not found | Old API | Use `gl.vm.run_nondet_unsafe` instead |
| `call_llm` not found | Old API | Use `gl.nondet.exec_prompt` instead |
| `get_webpage` not found | Old API | Use `gl.nondet.web.get` instead |
| `IContract` not found | Old API | Use `gl.Contract` instead |

---

## 7. Tolerance Reference Table

Based on empirical testing across multiple contract types:

| Use Case | Recommended Tolerance | Reason |
|----------|----------------------|--------|
| Binary classification (YES/NO) | Exact match | Fixed vocabulary, should always agree |
| Sentiment (POS/NEG/NEU) | Exact match | Fixed vocabulary |
| Numeric score (0-10) | ±2 points | LLM subjectivity |
| Confidence value (0-100) | ±10-15 points | LLM variation |
| Price/financial data | ±2% relative | Market movement between validators |
| Web content length | ±500 chars | Caching differences |
| Winner/verdict field | Exact match | Binary decision must be consistent |

---

## 8. Quick Checklist

Before deploying your Intelligent Contract:

```
✅ Header: # { "Depends": "py-genlayer:test" }
✅ Import: from genlayer import *
✅ Class inherits gl.Contract (not IContract)
✅ Constructor uses primitive types only (str, u256, bool)
✅ State variables declared at class level with type annotations
✅ Read functions use @gl.public.view
✅ Write functions use @gl.public.write
✅ LLM calls use gl.nondet.exec_prompt
✅ Web calls use gl.nondet.web.get
✅ Non-deterministic logic wrapped in gl.vm.run_nondet_unsafe
✅ validator_fn returns False on any exception
✅ JSON output uses sort_keys=True
✅ Web content truncated to [:2000]
✅ LLM output values validated and clamped
✅ Execution Mode set to Normal (Full Consensus) in Studio
```

---

## Resources

- [GenLayer Docs](https://docs.genlayer.com)
- [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [GenLayer Studio](https://studio.genlayer.com)
- [Collection Types](https://docs.genlayer.com/developers/intelligent-contracts/types/collections)
- [Discord](https://discord.gg/8Jm4v89VAu)

---

*Based on empirical testing building multiple Intelligent Contracts for the GenLayer Hackathon.*
