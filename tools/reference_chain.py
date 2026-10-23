#!/usr/bin/env python3
"""
Reference implementation of the compound generator chain.
Mirrors advance_chain in playthrough_sim.py using the exact rates from
CONFIG.generators in assets/game.html.

Scenario: formsworth=50, subclerk=10, datastack=5, others=0
Duration:  3600 s, dt=10 s (360 steps)
ccMultiplier = 1.0 (sun=0, no upgrades — isolated chain test)
"""
import json

# Must stay in sync with CONFIG.generators in assets/game.html
GENS = [
    {"id": "formsworth", "rate": 1.0},
    {"id": "subclerk",   "rate": 0.05},
    {"id": "datastack",  "rate": 0.004},
    {"id": "archive",    "rate": 0.00096},
    {"id": "sphere",     "rate": 0.000768},
    {"id": "census",     "rate": 0.000615},
    {"id": "ledger",     "rate": 0.000492},
]

counts = {g["id"]: 0.0 for g in GENS}
counts["formsworth"] = 50.0
counts["subclerk"]   = 10.0
counts["datastack"]  = 5.0
cc = 0.0

DT    = 10
STEPS = 3600 // DT

for _ in range(STEPS):
    # Top-down: tier N produces tier N-1 (indices 6→1)
    for i in range(len(GENS) - 1, 0, -1):
        counts[GENS[i - 1]["id"]] += counts[GENS[i]["id"]] * GENS[i]["rate"] * DT
    # T1 (formsworth) → CC; ccMultiplier = 1.0
    cc += counts["formsworth"] * GENS[0]["rate"] * DT

print(json.dumps({"genCounts": counts, "cc": cc}, indent=2))
