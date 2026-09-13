# Performance testing

The orchestration repository includes load-generation helpers, but it does not
currently publish a benchmark result. Reproduce a complete stack locally before
using these scripts; the public repository does not include the Go API or C++
engine source.

## Load generators

| Script | Purpose |
| --- | --- |
| [`scripts/distributed_load_test.py`](../scripts/distributed_load_test.py) | Drive a configured API endpoint with concurrent clients |
| [`scripts/aggregate_load_test.py`](../scripts/aggregate_load_test.py) | Aggregate a multi-process load run |

Review each script's command-line help before running it:

```bash
python scripts/distributed_load_test.py --help
python scripts/aggregate_load_test.py --help
```

## Record a useful run

For every result, retain:

- the orchestration, API, and engine commit IDs;
- immutable container image digests;
- CPU, memory, operating system, container runtime, and database versions;
- replica counts, resource limits, runtime settings, and database layout;
- the exact load-generator command, duration, concurrency, and request mix;
- raw output, exit status, errors, and any discarded attempts; and
- the script or calculation that produced each summary table or chart.

Repeat the same workload several times and report variation between runs. Label
configuration limits and design targets as targets, not measured throughput.

## Suggested result layout

```text
benchmarks/<date>-<scenario>/
├── README.md
├── revisions.json
├── environment.json
├── config/
├── raw/
└── summary/
```

The run README should state what was measured, how to repeat it, and which
conditions make comparisons invalid. Do not publish secrets or proprietary
component source in the result bundle.
