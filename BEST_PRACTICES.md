# GenLayer Intelligent Contract Best Practices Guide

A practical guide for developers building Intelligent Contracts on GenLayer. Based on empirical testing across multiple contract types achieving 100% consensus rate.

---

## Table of Contents

1. Contract Structure
2. Equivalence Principle Patterns
3. Prompt Engineering for Consensus
4. Web Fetch Best Practices
5. Storage Patterns
6. Common Errors and Fixes
7. Tolerance Reference Table
8. Quick Checklist
9. Payable Functions and gl.message
10. Access Control Patterns
11. TreeMap Storage
12. Testing Workflow
13. LEADER_TIMEOUT and Transaction Retries

---

## 1. Contract Structure

### Correct Minimal Contract Template

```python
# { "Depends": "py-genlayer:test" }

import json
from genlayer import *

class MyContract(gl.Contract):

    owner: Address
    counter: u256
    items: DynArray[str]

    def __init__(self, owner_address: str):
        self.owner = Address(owner_address)
        self.counter = u256(0)

    @gl.public.view
    def get_data(self) -> str:
        return f"Counter: {int(self.counter)}"

    @gl.public.write
    def do_something(self, input: str) -> str:
        self.counter = u256(int(self.counter) + 1)
        return f"Done: {input}"
```

The constructor always receives str and converts internally with Address(owner_address). This is required for GenLayer Studio to parse the contract schema correctly while keeping the internal type as Address for the genvm-lint check.

### Common Mistakes

```python
# WRONG: old syntax, does not work in GenLayer Studio
from genlayer import IContract, public

class MyContract(IContract):
    @public
    def my_function(self) -> str:
        result = call_llm("prompt")
        data = get_webpage(url, mode="text")

# CORRECT: current syntax
from genlayer import *

class MyContract(gl.Contract):
    @gl.public.write
    def my_function(self) -> str:
        result = gl.nondet.exec_prompt("prompt")
        response = gl.nondet.web.get(url)
        data = response.body.decode("utf-8")
```

### Address Type Pattern

The correct pattern for contracts that store an owner address is to declare Address as the state type but accept str in the constructor. This satisfies both GenLayer Studio and the genvm-lint validator.

```python
# WRONG for Studio: causes "Could not load contract schema"
class MyContract(gl.Contract):
    owner: Address
    def __init__(self, owner_address: Address):
        self.owner = owner_address

# CORRECT: works in Studio and passes genvm-lint
class MyContract(gl.Contract):
    owner: Address
    def __init__(self, owner_address: str):
        self.owner = Address(owner_address)
```

The same pattern applies to any method that receives an address as a parameter. Accept str and convert with Address() at the boundary.

---

## 2. Equivalence Principle Patterns

The Equivalence Principle is how GenLayer achieves consensus on non-deterministic operations. Always use gl.vm.run_nondet_unsafe with a leader_fn and validator_fn.

### Pattern 1: Exact Match

Use when output is a fixed set of values such as YES/NO or POSITIVE/NEGATIVE.

```python
def leader_fn():
    result = gl.nondet.exec_prompt("Classify as POSITIVE or NEGATIVE: ...")
    return result.strip().upper()

def validator_fn(leader_result) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    validator_out = leader_fn()
    return leader_result.calldata.strip() == validator_out.strip()

result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

### Pattern 2: Numeric Tolerance

Use when output is numeric and may vary slightly between validators.

```python
def validator_fn(leader_result) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    validator_raw = leader_fn()
    leader_data = json.loads(leader_result.calldata)
    validator_data = json.loads(validator_raw)
    return abs(leader_data["score"] - validator_data["score"]) <= 10
```

### Pattern 3: Field Matching

Use when output has multiple fields but only key fields matter for consensus.

```python
def validator_fn(leader_result) -> bool:
    if not isinstance(leader_result, gl.vm.Return):
        return False
    validator_raw = leader_fn()
    leader_data = json.loads(leader_result.calldata)
    validator_data = json.loads(validator_raw)
    return leader_data["verdict"] == validator_data["verdict"]
```

### Pattern 4: Web Fetch and LLM

The most common production pattern combining web fetch with LLM analysis.

```python
def leader_fn():
    response = gl.nondet.web.get(url)
    web_data = response.body.decode("utf-8")[:2000]
    result = gl.nondet.exec_prompt(f"Analyze: {web_data}")
    data = json.loads(result.strip().replace("```json","").replace("```",""))
    return json.dumps(data, sort_keys=True)

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
        return False

result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
```

---

## 3. Prompt Engineering for Consensus

Good prompts are critical for reliable consensus.

### Structure Your Prompts for Determinism

```python
prompt = f"""Analyze this topic and respond ONLY with a JSON object.
Topic: "{topic}"

{{"verdict": "POSITIVE", "confidence": 80, "reasoning": "one sentence"}}

Rules:
verdict must be exactly POSITIVE, NEGATIVE, or NEUTRAL
confidence must be an integer from 0 to 100
reasoning must be one sentence max
No extra text."""
```

### Use sort_keys=True When Returning JSON

```python
return json.dumps({"verdict": verdict, "confidence": conf}, sort_keys=True)
```

### Strip Markdown Fences

```python
clean = result.strip().replace("```json", "").replace("```", "").strip()
data = json.loads(clean)
```

### Validate and Clamp Output Values

```python
verdict = data.get("verdict", "NEUTRAL")
if verdict not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
    verdict = "NEUTRAL"

confidence = int(data.get("confidence", 50))
confidence = max(0, min(100, confidence))
```

### Avoid Open-Ended Text Without Structure

```python
# BAD
result = gl.nondet.exec_prompt("Tell me about Bitcoin")

# GOOD
result = gl.nondet.exec_prompt("""Analyze Bitcoin. Respond ONLY with JSON:
{"verdict": "POSITIVE", "confidence": 80}""")
```

### Do Not Return Raw LLM Text

```python
# BAD
return gl.nondet.exec_prompt(prompt)

# GOOD
raw = gl.nondet.exec_prompt(prompt)
data = json.loads(raw.strip())
return json.dumps({"verdict": data["verdict"]}, sort_keys=True)
```

---

## 4. Web Fetch Best Practices

### Always Truncate Web Content

```python
response = gl.nondet.web.get(url)
content = response.body.decode("utf-8")[:2000]
```

Truncating reduces LLM processing time, keeps content within prompt limits, and improves consistency across validators.

### Use Reliable and Stable URLs

Good sources include Wikipedia, official news APIs, government sites, and CoinGecko API. Avoid dynamic JS-rendered pages, pages requiring login, sites with aggressive caching, and sites that block scraping.

### Handle Fetch Errors Gracefully

Some APIs return non-JSON responses or unexpected formats. Always wrap parsing in a try-except and provide a safe fallback.

```python
def leader_fn():
    try:
        response = gl.nondet.web.get(url)
        raw_body = response.body.decode("utf-8")
        try:
            data = json.loads(raw_body)
        except Exception:
            data = None
        if not data or not isinstance(data, dict):
            return json.dumps({"result": "unavailable"}, sort_keys=True)
    except Exception:
        return json.dumps({"result": "unavailable"}, sort_keys=True)
```

### Use Wikipedia for Factual Queries

```python
url = f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}"
```

---

## 5. Storage Patterns

### Use DynArray[str] for Flexible Storage

```python
class MyContract(gl.Contract):
    data: DynArray[str]

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

### Always Initialize u256 Correctly

```python
# CORRECT
self.counter = u256(0)
self.counter = u256(int(self.counter) + 1)

# WRONG
self.counter = 0
self.counter += 1
```

### Avoid External Dataclasses for Constructor Args

```python
# This causes "Could not load contract schema" error in Studio
class MyContract(gl.Contract):
    def __init__(self, data: MyData):
        ...

# CORRECT
class MyContract(gl.Contract):
    def __init__(self, owner_address: str, name: str):
        ...
```

---

## 6. Common Errors and Fixes

Could not load contract schema is caused by complex constructor args, old syntax, or using Address directly as a constructor parameter type. Fix by using primitive types such as str, u256, and bool in the constructor, and convert to Address internally with Address(owner_address).

FINALIZED ERROR is caused by an assert failing or wrong state. Fix by checking function preconditions and state before calling.

Validator disagreement is caused by tolerance being too strict. Fix by increasing tolerance in validator_fn.

JSON parse error is caused by the LLM returning markdown. Fix by adding .replace("```json","").replace("```","") before parsing.

AttributeError NoneType has no attribute get is caused by an external API returning a non-JSON response or an empty body. Fix by wrapping json.loads in a try-except, checking if the result is a valid dict before accessing fields, and returning safe default values when data is unavailable.

gl.eq_principle_prompt_comparative not found means you are using the old API. Use gl.vm.run_nondet_unsafe instead.

gl.eq_principle.strict_eq not found in Studio means the testnet version does not support this method. Use gl.vm.run_nondet_unsafe with a custom validator_fn instead.

call_llm not found means you are using the old API. Use gl.nondet.exec_prompt instead.

get_webpage not found means you are using the old API. Use gl.nondet.web.get instead.

IContract not found means you are using the old API. Use gl.Contract instead.

---

## 7. Tolerance Reference Table

Binary classification such as YES/NO requires exact match because the vocabulary is fixed and validators should always agree.

Sentiment classification such as POSITIVE, NEGATIVE, or NEUTRAL requires exact match for the same reason.

Numeric scores from 0 to 10 allow a tolerance of plus or minus 2 points due to LLM subjectivity.

Confidence values from 0 to 100 allow a tolerance of plus or minus 10 to 15 points due to LLM variation.

Price and financial data allows a tolerance of plus or minus 2 percent relative to account for market movement between validators.

Web content length allows a tolerance of plus or minus 500 characters due to caching differences.

Winner and verdict fields require exact match because binary decisions must be consistent.

---

## 8. Quick Checklist

Before deploying your Intelligent Contract check the following.

The header line is # { "Depends": "py-genlayer:test" }

The import is from genlayer import *

The class inherits gl.Contract and not IContract

The constructor uses primitive types only such as str, u256, and bool

Address state variables are declared as Address but the constructor receives str and converts with Address(value)

State variables are declared at class level with type annotations

Read functions use @gl.public.view

Write functions use @gl.public.write

LLM calls use gl.nondet.exec_prompt

Web calls use gl.nondet.web.get

Web fetch responses are wrapped in try-except before JSON parsing

Non-deterministic logic is wrapped in gl.vm.run_nondet_unsafe

validator_fn returns False on any exception

JSON output uses sort_keys=True

Web content is truncated to the first 2000 characters

LLM output values are validated and clamped

Execution mode is set to Normal Full Consensus in Studio

Payable functions assert gl.message.value >= fee before executing

Owner-only functions assert gl.message.sender_address == self.owner

TreeMap is used for key-value lookups when the key set can grow

genvm-lint check passes before every deploy

Contract tested in Direct mode before Full Consensus mode

LEADER_TIMEOUT is handled by resubmitting, not by modifying the contract

---

## 9. Payable Functions and gl.message

### Accepting GEN Token Payments

Use `gl.message.value` to read the amount of GEN sent with a transaction. Always assert the minimum fee before executing logic.

```python
@gl.public.write
def scan_token(self, token_address: str, chain: str) -> None:
    assert gl.message.value >= self.fee, "Insufficient GEN fee"
    self.treasury = u256(int(self.treasury) + int(gl.message.value))
    # proceed with logic
```

### The gl.message Object

`gl.message` is available in any write function and exposes two fields.

`gl.message.sender_address` returns the Address of the caller. Use this to identify who is calling the function and to enforce ownership checks.

`gl.message.value` returns the amount of GEN (in wei) sent with the transaction as a u256. One GEN equals 10^18 wei.

```python
@gl.public.write
def deposit(self) -> None:
    caller = gl.message.sender_address       # Address
    amount = gl.message.value                # u256, in wei
    assert amount > u256(0), "Send GEN to deposit"
    self.balances[str(caller)] = u256(
        int(self.balances.get(str(caller), u256(0))) + int(amount)
    )
```

### Fee Constants in Wei

Define fee constants at the top of the contract to avoid magic numbers.

```python
FEE_SCAN    = u256(500_000_000_000_000_000)   # 0.5 GEN
FEE_WALLET  = u256(1_000_000_000_000_000_000) # 1.0 GEN
FEE_RADAR   = u256(300_000_000_000_000_000)   # 0.3 GEN
```

### Withdrawal Pattern

Owner-only function to withdraw accumulated fees from the treasury.

```python
@gl.public.write
def withdraw_treasury(self, amount_wei: u256) -> None:
    assert gl.message.sender_address == self.owner, "Not owner"
    assert amount_wei <= self.treasury, "Insufficient treasury"
    self.treasury = u256(int(self.treasury) - int(amount_wei))
    # In GenLayer the transfer is recorded in the transaction messages field
```

---

## 10. Access Control Patterns

### Owner-Only Functions

Always assert the caller is the owner at the top of restricted functions. There are no modifiers in GenLayer contracts, so repeat the check explicitly.

```python
class MyContract(gl.Contract):
    owner: Address

    def __init__(self, owner_address: str):
        self.owner = Address(owner_address)

    @gl.public.write
    def admin_action(self, value: str) -> None:
        assert gl.message.sender_address == self.owner, "Not owner"
        # restricted logic here

    @gl.public.write
    def transfer_ownership(self, new_owner: str) -> None:
        assert gl.message.sender_address == self.owner, "Not owner"
        self.owner = Address(new_owner)
```

### Checking Ownership in View Functions

View functions cannot assert or revert. Return a boolean flag instead.

```python
@gl.public.view
def is_owner(self, addr: str) -> bool:
    return Address(addr) == self.owner
```

### Multi-Role Pattern

For contracts with more than one privileged role, store roles as a DynArray of addresses.

```python
class MyContract(gl.Contract):
    owner:      Address
    operators:  DynArray[str]

    @gl.public.write
    def add_operator(self, addr: str) -> None:
        assert gl.message.sender_address == self.owner, "Not owner"
        if addr not in self.operators:
            self.operators.append(addr)

    def _is_operator(self, addr: Address) -> bool:
        return str(addr) in self.operators
```

---

## 11. TreeMap Storage

### TreeMap vs DynArray

Use `TreeMap` when you need fast key-value lookups. Use `DynArray[str]` only when you need ordered iteration or the key set is small. TreeMap is more idiomatic and does not require manual prefix parsing.

```python
from genlayer import *

class MyContract(gl.Contract):
    # Key-value: wallet address -> score
    scores: TreeMap[str, u256]

    @gl.public.write
    def set_score(self, wallet: str, score: u256) -> None:
        self.scores[wallet] = score

    @gl.public.view
    def get_score(self, wallet: str) -> u256:
        return self.scores.get(wallet, u256(0))
```

### Nested Data Pattern

For two-level key-value structures, store serialized JSON as the value rather than nesting TreeMaps.

```python
class MyContract(gl.Contract):
    # market_id -> serialized JSON metadata
    markets: TreeMap[str, str]

    def _get_market(self, market_id: str) -> dict:
        raw = self.markets.get(market_id, "{}")
        return json.loads(raw)

    def _set_market(self, market_id: str, data: dict) -> None:
        self.markets[market_id] = json.dumps(data, sort_keys=True)
```

### When to Use DynArray vs TreeMap

Use DynArray when you need to iterate over all entries, maintain insertion order, or store a flat list of items. Use TreeMap when you need fast lookups by key, the key set can grow large, or you are building a registry or mapping pattern.

---

## 12. Testing Workflow

### Step 1: Lint Before Every Deploy

Run genvm-lint after every change and before deploying. Fix all errors before proceeding.

```bash
genvm-lint check contracts/my_contract.py
```

A clean output looks like this.

```
✓ Lint passed (3 checks)
✓ Validation passed
  Contract: MyContract
  Methods: 8 (5 view, 3 write)
```

### Step 2: Test in Direct Mode First

Direct mode runs only the leader node without validators. It is fast and useful for catching logic errors and JSON parsing issues before running full consensus.

In GenLayer Studio, set the execution mode to **Direct** and call your write functions. Check that return values and state changes are correct.

### Step 3: Test in Full Consensus Mode

Full consensus runs all validators and applies the Equivalence Principle. Set execution mode to **Normal Full Consensus** in Studio.

Run each write function and verify that the transaction finalizes without validator disagreement. If validators disagree, increase the tolerance in your `validator_fn`.

### Step 4: Verify State with View Functions

After each write transaction finalizes, call the corresponding view functions to confirm state was updated correctly.

```python
# After calling set_score(wallet, score), verify with:
get_score(wallet)  # should return the value you set
```

### Step 5: Test Edge Cases

Always test with missing data, empty strings, and invalid addresses before deploying to a shared environment.

---

## 13. LEADER_TIMEOUT and Transaction Retries

### What LEADER_TIMEOUT Means

LEADER_TIMEOUT occurs when the designated leader node does not respond within the expected window. This is a network-level event, not a bug in your contract. When it happens, GenLayer automatically promotes the next validator to leader and retries the round.

From the user's perspective the transaction may appear to hang or show a LEADER_TIMEOUT status before eventually finalizing. This is normal behavior on Studionet.

### What to Do

Do not modify your contract when you see LEADER_TIMEOUT. Simply resubmit the transaction. The most common cause is temporary validator unavailability on the test network.

```
Transaction status: LEADER_TIMEOUT
Action: Resubmit the same transaction
Result: Usually finalizes on the second or third attempt
```

### Distinguishing LEADER_TIMEOUT from a Real Error

LEADER_TIMEOUT never produces a state change. If the transaction showed LEADER_TIMEOUT and then you resubmit and it finalizes successfully, the contract is working correctly.

A real error produces a FINALIZED status with an error message in the transaction detail. This means an assert failed or the contract threw an exception.

### Reducing LEADER_TIMEOUT Frequency

Long-running `leader_fn` functions increase the chance of timeout. Keep web fetches to one or two URLs per transaction, truncate web content to 2000 characters, and keep prompts concise. The faster the leader completes, the less likely validators are to time out.

---

## Resources

GenLayer Docs: https://docs.genlayer.com

Equivalence Principle: https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle

Address Type: https://docs.genlayer.com/developers/intelligent-contracts/types/address

GenLayer Studio: https://studio.genlayer.com

Collection Types: https://docs.genlayer.com/developers/intelligent-contracts/types/collections

Discord: https://discord.gg/8Jm4v89VAu


    
