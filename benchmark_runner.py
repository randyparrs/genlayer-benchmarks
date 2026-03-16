# benchmark_runner.py
# Automated benchmark runner for GenLayer Intelligent Contracts

import time
import statistics
import argparse


def run_benchmark(client, contract_address, method, args, runs=10):
    """
    Run a benchmark method N times and collect timing data.
    Returns a dict with timing statistics.
    """
    times = []
    consensus_rates = []

    print(f"\nRunning {runs} iterations of {method}...")
    print("-" * 50)

    for i in range(runs):
        start = time.time()

        tx_hash = client.write_contract(
            address=contract_address,
            function=method,
            args=args,
        )

        receipt = client.wait_for_receipt(tx_hash, timeout=120)
        elapsed = time.time() - start
        times.append(elapsed)

        agreed = receipt.get("consensus_data", {}).get("validators_agreed", 5)
        consensus_rates.append(agreed == 5)

        print(f"Run {i+1:2d}: {elapsed:.2f}s  Status={receipt['status']}  "
              f"Agree={agreed}/5")

    print("-" * 50)
    print(f"Average:        {statistics.mean(times):.2f}s")
    print(f"StdDev:         {statistics.stdev(times):.2f}s")
    print(f"Min:            {min(times):.2f}s")
    print(f"Max:            {max(times):.2f}s")
    print(f"Consensus rate: {sum(consensus_rates)/len(consensus_rates)*100:.1f}%")

    return {
        "method": method,
        "runs": runs,
        "avg": statistics.mean(times),
        "stdev": statistics.stdev(times),
        "min": min(times),
        "max": max(times),
        "consensus_rate": sum(consensus_rates) / len(consensus_rates),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GenLayer Benchmark Runner")
    parser.add_argument("--contract", required=True, help="Contract name (BM01, BM02...)")
    parser.add_argument("--runs", type=int, default=10, help="Number of runs")
    args = parser.parse_args()

    print(f"GenLayer Performance Benchmark Runner")
    print(f"Contract: {args.contract}  Runs: {args.runs}")
