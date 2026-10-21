# BALANCE.md — Galactic Bureaucracy

> Every tunable number, its current value, what it affects, and how to tune safely.
> Source of truth = `galactic_bureaucracy_economy.xlsx` (Assumptions sheet). The simulator
> `playthrough_sim.py` reads these live, so the loop is: **edit sheet → re-run sim → check
> pacing → port to JS**. Numbers below are current as of the compound-model rebuild.

---

## Implementation Note — `genPurchased` vs. `genCounts` (game.html)

The simulator prices the next purchase as `base_cost × 1.25^floor(genCounts[id])`, where
`genCounts` includes fractionally-produced units from the compound chain. **game.html uses a
separate `genPurchased` counter** (integer, manual buys only) as the cost exponent instead.
This is a conscious deviation: counting fractional produced units in the price would
penalise players who progressed naturally through idle play. In practice the difference is
small early-game but widens at high generator counts. If playtesting shows generators feel
too cheap in late-stage runs, switch the exponent to `Math.floor(state.genCounts[id])` and
re-validate against the sim.

---

## 0. The tuning workflow (read first)

1. Open `galactic_bureaucracy_economy.xlsx`. All tunable cells are **blue on yellow** in the
   Assumptions sheet (and the generator/ship/research sheets).
2. Change a value. Save.
3. `python recalc.py galactic_bureaucracy_economy.xlsx` (recomputes formulas, checks errors).
4. `python playthrough_sim.py 40` (simulate 40 days; arg = number of days).
5. Read the **MILESTONES**, **PROGRESSION SNAPSHOTS**, **RED PILL ECONOMY**, and **HEALTH
   FLAGS** sections of the output. `playthrough_log.csv` has the full per-session series.
6. When it feels right, port the changed numbers into the JS `CONFIG` (see claude.md §11).

**Golden rule:** change ONE knob at a time and re-sim. Compound economies are sensitive;
multiple simultaneous changes make it impossible to see what caused what.

---

## 1. Global / core knobs

| Knob | Current | Effect |
|------|---------|--------|
| Tick rate | 1 /s | Production resolves per second. Keep at 1 for design clarity. |
| Session length (active) | 5 min | Modeled active session length (sim only). |
| Offline cap | 8 h | Max offline accrual. A return trigger, NOT a punishment. |
| Offline efficiency | 0.5× | Offline earns half the online rate. |
| Manual click yield | 1 CC/tap | Real players mash 5–8/s → first generator in ~8s. Manual phase is intentionally tiny. |
| Rewarded ad multiplier | 2× | Watch-ad reward: double offline haul or skip a war timer. |

---

## 2. Compound generator chain (the CC engine)  — `CC_Generators` sheet

**This is the most sensitive system. Tune base rates and costs with extreme care.**

| Tier | Generator | Base rate /s | Base cost | Cost mult | Unlock |
|------|-----------|--------------|-----------|-----------|--------|
| 1 | Lord Formsworth III | 1.0 (→CC) | 40 | 1.25 | start |
| 2 | Sub-Clerk Battalion | 0.0005 | 800 | 1.25 | 5k CC |
| 3 | Regional Datastack | 0.0004 | 60,000 | 1.25 | 500k CC |
| 4 | Orbital Archive | 0.00032 | 9e6 | 1.25 | conquer Inner |
| 5 | Sector Bureaucphere | 0.000256 | 1.6e9 | 1.25 | conquer Mid |
| 6 | Galactic Census Engine | 0.000205 | 3.2e11 | 1.25 | conquer Outer |
| 7 | The Infinite Ledger | 0.000164 | 7.2e13 | 1.25 | conquer Fringe |

- **Base rate** = how fast a tier produces the tier below. **Higher rate = far more explosive**
  (these compound down the chain). The current values were calibrated from a runaway raw model
  (0.10/tier gave 4.6×10²⁴ CC/s by day 25) down to a clean curve. Treat ~0.0005 as the safe
  ceiling for tier-2; raising it re-ignites runaway fast.
- **Base cost / cost mult (1.25)** keep high tiers rare. Lowering cost mult → you own more of each
  tier → faster compounding. Raising costs is the safest brake on the curve.
- Validated curve (current values): **~12 CC/s at start → ~25 trillion/s by day ~38**, always
  accelerating, conquest unlocks driving visible leaps (days ~4, 10, 20, 32).
- **If the number explodes too fast:** raise costs and/or lower tier-2/3 base rates first.
- **If it feels flat/slow:** lower costs slightly or nudge base rates up by ~20% and re-sim.
- Calibration helper: `calibrate.py` sweeps a rate scale and prints CC/s at days 1/5/10/18.

---

## 3. War / conquest  — `War_Sim` sheet

| Knob | Current | Effect |
|------|---------|--------|
| Base war timer | 6 h | Tier-1 conquest timer. Scales ×1.5/tier. |
| Red Pill per Mech-Bro | 25 | Enlist cost per unit. |
| Tier cost scale | 4× /tier | Red Pill cost multiplier per sector tier. |
| Tier output scale | 3× /tier | Region resource output per tier. |
| Tier timer scale | 1.5× /tier | War timer per tier (Fringe wars are long). |
| Sector unlock % | 0.6 | Fraction of a sector to hold before next unlocks (capital does this now). |
| **Mech-Bro base (tier1)** | 8 | Base army for a tier-1 region. |
| **Mech-Bro tier scale** | 5× /tier | Army size per tier. Base 8 → Fringe ~5,000. **The army wall.** |

- Army formula: `round(8 × 5^(tier-1) × (1 + 0.1×regionIndex))`.
- ⚠ The ×5 scaling is steep by design (you asked for ~5000 at Fringe). It interacts hard with
  fleet capacity — see §4. If the deep game feels unreachable, lower mech tier scale to 4×.

### Red Pill economy (hybrid)
| Knob | Current | Effect |
|------|---------|--------|
| CC→Red Pill primer rate | 0.00002 RP per CC/s | Bootstrap trickle only (cut 100× from old 0.002). |
| **Red Pill primer cap** | **2 RP/s (hard cap)** | Absolute ceiling on primer income. THE key fix — see note. |
| Region Red Pill drop (tier1) | 2.0 RP/s | Base Red Pill income per conquered tier-1 region. |
| Red Pill tier scale | 3.0× /tier | Deeper regions pay more Red Pill (snowball). |
| Resource-region RP modifier | 0.4× | Sun/Melange regions pay only 40% Red Pill (economy OR war). |

- ⚠ **Why the cap exists (compound-economy fix):** the primer is `CC/s × primer_rate`. Under the
  compound chain, CC/s reaches trillions, so an uncapped primer became a multi-million-RP/s
  *firehose* that dwarfed region income and made war effectively free. The hard cap (2 RP/s)
  forces the primer to stay a true bootstrap; conquered-region drops are the only war income
  that scales. Validated: region income crosses the (capped) primer permanently by **day 2**.
- To make war richer, raise the **region drop / tier scale**, NOT the primer. To make the early
  bootstrap faster, raise the **cap** (carefully — it's a flat RP/s, very powerful early).


### Factions & capitals
| Knob | Current | Effect |
|------|---------|--------|
| Capital army base mult | 5× | Inner capital = 5× its normal region army. |
| Capital mult per tier | 1.5× /tier | Capital multiplier grows; Fringe capital ~17× (~84k army). |

- Capital = boss region; taking it eliminates the faction → unlocks next sector + unique vassal
  (+25% permanent production).

---

## 4. Fleet & ships  — `Fleet_Sim` / `Research_Sim` sheets

| Knob | Current | Effect |
|------|---------|--------|
| CC per Transit Visa | 100 | Brutal CC→Visa conversion. Visas gate the fleet. |

Ships (additive: **fleet capacity = sum of all built ships**):

| Ship | Research CC | Research hrs | Res gate | Visa cost | Capacity | Range |
|------|-------------|--------------|----------|-----------|----------|-------|
| Shuttle | 0 | 0 | – | 1,000 | 5 | 1 |
| Frigate | 50,000 | 4 | – | 6,000 | 30 | 2 |
| Cruiser | 500,000 | 10 | T2 | 30,000 | 120 | 3 |
| Dreadnought | 5,000,000 | 24 | T3 | 150,000 | 400 | 4 |
| Leviathan | 50,000,000 | 48 | T4 | 600,000 | 1,200 | 5 |

- **Capacity vs range:** smaller ships are more Visa-efficient per capacity but limited range;
  big ships reach deep sectors. You can't cheese the Fringe with a swarm of shuttles (range gate).
- A Fringe capital (~84k army) needs ~70 Leviathans — an intentional armada-building endgame.
- If the late fleet grind feels too heavy, lower Leviathan Visa cost or raise its capacity.

### ⚠ Two structural rules added in the compound rebalance (read these)

1. **Wars run in PARALLEL, bounded by uncommitted fleet capacity.** A war reserves capacity equal
   to its army for its whole timer; you can launch another war only if your *remaining* (free)
   capacity covers it. Capacity frees up when a war resolves. So fleet size now controls *how many
   simultaneous campaigns* you can run, not just how big a single one can be — this is the main
   reason the early game hits its pace (one-war-at-a-time capped conquest at ~4 regions/day, which
   pushed the first wall out to ~day 20; parallel wars bring it to ~day 5). To slow conquest down,
   raise army sizes or Visa costs; to speed it up, cheapen the fleet.
2. **Deep-space RANGE is gated by PRESTIGE, not by ships.** A ship grants its hull range, but a
   hard cap of `BASE_REACH(=3) + perm_range_bonus` limits how deep you can actually go. With zero
   prestiges you reach **tier 3** (you wall at ~32/54); each Abdication permanently +1 tier
   (prestige 1 → tier 4, prestige 2 → tier 5/Fringe). **This is what makes prestige a HARD GATE.**
   Previously ships alone granted full range, so prestige never needed to fire.


---

## 5. Sun Drips connection buff  — `Connections_Sim` sheet

| Knob | Current | Effect |
|------|---------|--------|
| Connection buff per link | 0.03 (3%) | Per-link LOCAL buff to that system's own output. |
| Max links counted/system | 3 | Per-system cap → ceiling 9% from links. |
| Supply-line bonus | 0.05 (5%) | +5% if linked to another conquered Sun Drips system. |
| Sun Drips → CC boost (global) | 0.005 (0.5%/drip) | TINY global lever toward prestige threshold. Capped +200%. |

- Per-system hard ceiling: **14%** (3×3% + 5%). Bounded by construction.
- ⚠ Do NOT raise the global Sun→CC boost much — a previous 10%/drip caused a +2,810% runaway.
  The LOCAL buff is the real mechanic; the global one is a tiny intentional nudge only.

---

## 6. Tier-resource production sinks  — `ResourceLadder_Sim` sheet

| Knob | Current | Effect |
|------|---------|--------|
| Resource-region prod bonus | 0.03 (+3%) | Each conquered resource region boosts CC production. |
| Prod bonus diminish | 0.85 | Each successive region worth 0.85^n of the last (bounded). |
| Tier4 res → CC mult | 0.05 (+5%) | Deep resource regions add stronger direct CC. |
| Resource rate step | 3× /tier | Each tier's resource produces 3× faster than the last. |
| Tier2 res → Visa discount | 0.02 | Tier-2 resource regions slightly cut Visa cost. |
| Melange → compound rate | 0.05 | Melange refinement sink (compound CC). |
| Dark Matter yield (Fringe) | 0.001 DM/s per unit | Fringe resource → Dark Matter (prestige fuel). |

- These exist to keep CC climbing during conquest (kills mid-game plateau). Raising the prod
  bonus makes conquest more economically rewarding but can outpace the generator chain — re-sim.

---

## 7. Upgrade tree  — `UpgradeTree_Sim` sheet

| Branch | Effect/level | Base cost | Archetype |
|--------|--------------|-----------|-----------|
| Crystal Overclock | +10% CC | 100 | production multiplier |
| Expedited Warfare | −5% war timer | 250 | time saver |
| Bulk Enlistment | −4% Red Pill/Mech-Bro | 200 | cost reducer |

- Cost growth: ×2 per level. Always something affordable → no deadlock.

---

## 8. Prestige (Abdication)  — `Prestige_Sim` sheet

| Knob | Current | Effect |
|------|---------|--------|
| First-prestige buff | 0.5 | Per-prestige FLOOR base: buff floor = (1+0.5)^prestige_count (see formula). |
| Stamp buff per stamp | 0.6 | Multiplier on the LOG stamp bonus (NOT linear per-stamp anymore). |
| Prestige divisor | 1,000,000,000 | Stamps = floor((lifetimeCC/1e9)^0.5). Raised 20,000× for compound CC. |
| Prestige curve power | 0.5 (sqrt) | Diminishing stamps per run. |
| Dormant territory rate | 0.25 | Kept planets produce 0.25× until economy re-ramps. |
| Permanent range / prestige | +1 tier (cap +2) | Each prestige permanently raises reachable tier; see Fleet §4. |

- **Buff formula (rewritten — was a +6,478× runaway):**
  `prestige_mult = (1 + firstBuff)^prestige_count × (1 + stampBuff × log10(stamps + 1))`
  - The **floor** `(1.5)^n` guarantees each run is stronger than the last regardless of stamps —
    this is what stops the death-spiral (a reset with too weak a buff can't rebuild past the wall).
  - The **log stamp term** keeps buffs bounded under a compound economy. Linear stamp stacking
    (old `stamps × 0.02`) gave one prestige +6,478× because stamps scale as √(lifetimeCC) and
    lifetime hits ~10¹⁵. `log10` tames it: validated mults are ~2.5× (P1), ~5.3× (P2), ~14× (P3).
- Reset: CC, generators, Red Pill, Visas, research, upgrades, fleet.
- Keep: territory (dormant), stamps, faction vassals, permanent fleet range.
- **Validated cadence: P1 ≈ day 5 (walls at 32/54), P2 ≈ day 11, full 54/54 clear ≈ day 33.**
  The final Fringe capital (~84k army) is the climactic armada boss — a 2–3 prestige goal.

---

## 9. ⚠ KNOWN OPEN BALANCE ITEMS (start here)

1. **✅ RESOLVED — Prestige is now a HARD GATE.** Decision taken: Fringe is unreachable without
   prestige. Implemented via prestige-gated range (Fleet §4, rule 2): first run caps at tier 3,
   each Abdication +1 tier. The old "soft/optional prestige" problem is gone — you physically
   cannot pass tier 3 without prestige 1, nor reach the Fringe without prestige 2.
2. **✅ RESOLVED — First-wall depth & timing.** Wall now bites at **32/54 (tier 3) ≈ day 5**
   (target was ~30/54, snappy/mobile). Tuned via prestige-gated range + parallel wars (Fleet §4,
   rule 1) rather than by inflating army/Visa walls. If you want the wall *later*, lengthen war
   timers or slow the stall→prestige trigger; *earlier* isn't recommended (would wall mid-tier-2).
2. **First-run wall depth.** Ideally a first wall bites ~30/54 so the first prestige feels
   transformative; currently it's softer/deeper. Tune via deep army scale + Visa costs.
3. **Mid-run soft plateau** (~days 11–17 in older runs) — mostly fixed by tier-resource sinks;
   verify it stays gone under final numbers.
4. **War timer 6h vs 16h** — still worth playtesting for feel (return cadence).
5. **Dark Matter** now has a role (Fringe resource → prestige fuel) but its exact prestige
   multiplier formula is unspecified — define when building prestige depth.
6. **Sim models a disciplined 4-sessions/day player.** Real mash rates and irregular play will
   shift day-counts; the curve SHAPE is what's validated, not exact calendar days.

---

## 10. Files

- `galactic_bureaucracy_economy.xlsx` — the live model (13 sheets). Tune the blue cells.
- `playthrough_sim.py` — multi-day simulator; reads the sheet live. `python playthrough_sim.py N`.
- `playthrough_log.csv` — full per-session series from the last sim run.
- `calibrate.py` — base-rate sweep helper for the compound chain.
- `claude.md` — architecture + data shape + build order.
