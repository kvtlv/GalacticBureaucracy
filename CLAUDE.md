@AGENTS.md

# Galactic Bureaucracy — Claude Code Context

> Build & architecture reference for Claude Code. Pair this with [`docs/v0.2/BALANCE.md`](docs/v0.2/BALANCE.md) (every
> tunable number) and `design/economy-model/galactic_bureaucracy_economy.xlsx` (the live economy model) +
> `design/economy-model/playthrough_sim.py` (the simulator that validates pacing).

---

## 1. What this game is

An **idle / incremental** mobile game (built in **JavaScript**). The player is a galactic
emperor whose empire runs on absurd bureaucracy. Core fantasy: an economy that
**metastasizes faster than anyone can control it** — power fantasy + comedy.

Design pillars (do not violate without reason):
- **First 30 seconds: something grows.** Manual tap → first generator automates → dopamine.
- **No grind, only momentum.** The number is always visibly moving.
- **Waiting is a return reason, not a punishment.** Offline accrual is capped, not penalized.
- **One real strategic choice:** which region/sector to conquer (resource vs war-income tradeoff).
- **ADHD-first:** fast satisfaction, early hook, short sessions.

---

## Tech Stack

- Game logic: pure HTML/CSS/JS — single file at `assets/game.html`
- Shell: **Expo** (React Native) app that loads the game in a **WebView**
- No frameworks or build step inside `game.html`
- Target: iOS + Android via Expo / EAS Build → store release
- Stable Diffusion for art assets (planned, not yet added)

---

## File Structure

```
assets/
  game.html            ← entire game (single file, rendered inside Expo WebView)
  adaptive-icon.png
  favicon.png
  icon.png
  splash-icon.png
CLAUDE.md              ← this file
docs/v0.2/
  CLAUDE.md            ← full design document (authoritative source; this file is derived from it)
  BALANCE.md           ← all numeric constants and tuning guide
design/economy-model/  ← economy model & simulator (see §Economy Model below — not in code yet)
```

All tunable numbers live in [`docs/v0.2/BALANCE.md`](docs/v0.2/BALANCE.md). Never hardcode constants in game logic.

---

## Economy Model (`design/economy-model/`) — Not in Code Yet

`design/economy-model/` holds a fully specified economy model for the v0.3+ design: a 7-tier compound generator chain, a 5-sector conquest map (~54 conquerable nodes), an additive fleet system with 5 ship classes (Shuttle → Leviathan), faction capitals with unique vassal rewards, and a prestige/range hard-gate system, all validated by `playthrough_sim.py` against a 40-day simulated playthrough. Numbers are source-of-truth in `galactic_bureaucracy_economy.xlsx` (blue cells on the Assumptions sheet), cross-referenced in `ECONOMY-BALANCE.md`, and the full architecture + JS data shape live in `ARCHITECTURE.md`. **None of this expanded system is implemented in `assets/game.html` yet** — these files are the design target; implementation follows the build order in `ARCHITECTURE.md §13`.

---

## 2. The economy in one paragraph

Cyber Crystal (CC) is the spine. CC is produced by a **compound generator chain** (see §3):
each generator tier produces *the tier below it*, and only Tier 1 (Lord Formsworth) mints
CC — so production **accelerates over time**, even while idle. CC buys generators, ships
(via Transit Visas), research, and upgrades. **Conquest** (the War loop) unlocks deeper
generator tiers and yields aux resources (Sun Drips, Pepper Melange) that feed back into CC.
**Prestige** (Abdication) resets the economy but keeps territory, granting permanent buffs —
it's the long-term engine that breaks the late-game wall.

---

## 3. Generator chain (the CC engine) — COMPOUND model

This is the heart of the game and the most important thing to implement correctly.

**Rule:** Each tick, Tier N produces `count_N × rate_N × dt` units of **Tier N-1**.
Only Tier 1 produces CC. Higher tiers grow the tiers below them → compounding.

| Tier | Generator (vassal)        | Produces        | Base rate /s | Base cost      |
|------|---------------------------|-----------------|--------------|----------------|
| 1    | Lord Formsworth III       | Cyber Crystal   | 1.0          | 40             |
| 2    | Sub-Clerk Battalion       | Formsworths     | 0.0005       | 800            |
| 3    | Regional Datastack        | Sub-Clerks      | 0.0004       | 60,000         |
| 4    | Orbital Archive           | Datastacks      | 0.00032      | 9,000,000      |
| 5    | Sector Bureaucphere       | Archives        | 0.000256     | 1,600,000,000  |
| 6    | Galactic Census Engine    | Bureaucspheres  | 0.000205     | 320,000,000,000|
| 7    | The Infinite Ledger       | Census Engines  | 0.000164     | 72,000,000,000,000 |

- Per-generator cost curve: `cost(n) = base_cost × 1.25^n` (n = count already owned).
- **Unlocks:** T1 start; T2 at 5k lifetime CC; T3 at 500k CC; T4 conquer Inner sector;
  T5 conquer Mid; T6 conquer Outer; T7 conquer Fringe. (Early = CC milestone, deep = conquest.)
- Counts are **fractional** (a tier accretes partial units of the tier below). Store as floats.
- Implementation tick: resolve top-down (T7→T2 grow the tier below; T1 → CC) each frame/second.
  Sub-step long offline gaps (e.g. hourly chunks) so compounding accrues correctly.

This produces the validated curve: ~12 CC/s at start → ~25 trillion/s by day ~38, always
accelerating. See `design/economy-model/playthrough_sim.py::advance_chain` for the reference implementation.

---

## 4. Currencies

| Currency          | Role                        | Notes |
|-------------------|-----------------------------|-------|
| **Cyber Crystal (CC)** | Main currency             | Compound chain output; buys everything |
| **Sun Drips**     | Aux resource                | From conquered Sun regions; LOCAL connection buff (see §6) |
| **Pepper Melange**| Aux resource                | From conquered Melange regions; compound/refine sink |
| **Red Pill**      | War currency                | Enlists Mech-Bros; hybrid income (see §5) |
| **Mech-Bro**      | War unit (disposable)       | Army size needed to conquer; scales exponentially |
| **Transit Visa**  | Fleet currency              | Converted from CC (steep); builds ships. *Comedy: paperwork blocks your armada* |
| **Abdication Stamp** | Prestige unit            | Earned on prestige; permanent +production buff |
| **Dark Matter**   | Endgame / prestige fuel     | Fringe (deepest) resource; supercharges prestige |

---

## 5. War / Conquest loop

- Galaxy = **5 sectors × ~10 regions + 1 capital each = ~54 conquerable nodes.**
  Sectors are tiers 1–5 (Core, Inner, Mid, Outer, Fringe). Tier scales everything up.
- **Each region needs:** an army (Mech-Bros, enlisted with Red Pill) AND lift (fleet capacity).
  Conquest runs on a **timer** (hours), then the region is yours. **Wars run in PARALLEL:** each
  in-flight war reserves capacity = its army; you may launch another war whenever your *remaining*
  (uncommitted) capacity covers it. Fleet size therefore sets how many concurrent campaigns you
  can run, and is the main lever on conquest pace.
- **Mech-Bro requirement scales exponentially:** `base 8 × 5^(tier-1) × (1 + 0.1×index)`.
  Core ~8, Fringe regions ~5,000–9,500. This is the **army wall**.
- **Red Pill economy is HYBRID:** a small CC→Red Pill primer trickle bootstraps the first
  ~1 conquest, then conquered regions yield Red Pill (tier-scaled). Resource regions
  (Sun/Melange) pay only 0.4× Red Pill — *a region feeds your economy OR your war, rarely both.*
- **Region Red Pill income** crosses over the primer ~day 1 → war becomes self-funding.

### Factions & Capitals
- Each sector (tier 2+) is a hostile **faction** with a **capital** = boss region.
- Capital army = `normal_region_army × (5 × 1.5^(tier-2))`. Inner ~5×, Fringe ~17× (≈84k army).
- Taking a capital **eliminates the faction → unlocks next sector + grants a unique vassal**
  (permanent +25% production, survives prestige). Defeated empires leave behind a bureaucrat.
- The deepest capital (Fringe, ~84k army) is the climactic boss — a "build an armada of dozens
  of Leviathans" moment, intended as a multi-prestige goal.

---

## 6. Fleet & Ships (additive fleet model)

- **Fleet capacity = SUM of all built ships' capacities** (you build MANY ships, not one).
- Ships have **capacity** AND **range** (max reachable sector tier). Smaller ships are more
  Visa-efficient per capacity but limited range; only big ships reach deep sectors.
- Ships are **researched** (CC + a timer; deep tiers also gated by conquered-tier resources)
  then **built** (Transit Visas).

| Ship        | Research CC | Research time | Resource gate | Build (Visas) | Capacity | Range (tier) |
|-------------|-------------|---------------|---------------|---------------|----------|--------------|
| Shuttle     | 0 (instant) | 0             | none          | 1,000         | 5        | 1 |
| Frigate     | 50,000      | 4h            | none          | 6,000         | 30       | 2 |
| Cruiser     | 500,000     | 10h           | Tier-2 res    | 30,000        | 120      | 3 |
| Dreadnought | 5,000,000   | 24h           | Tier-3 res    | 150,000       | 400      | 4 |
| Leviathan   | 50,000,000  | 48h           | Tier-4 res    | 600,000       | 1,200    | 5 |

- Transit Visas convert from CC at **100 CC : 1 Visa** (deliberately brutal).
- Research timers are a return hook; a Frigate is "start research, come back in 4h."

---

## 7. Sun Drips connection buff (LOCAL, bounded by construction)

- Buff is **per-system and local** — each Sun Drips system is buffed by ITS OWN connections,
  NOT a global multiplier. (An earlier global version caused a +2,810% runaway bug — do NOT
  reintroduce a global per-drip multiplier.)
- `system_buff = min(links, 3) × 3% + (5% if linked to another conquered Sun Drips system)`.
- Hard ceiling per system: **14%** (3 links × 3% + 5% supply line). Rewards contiguous territory.
- There is also a TINY global Sun→CC boost (0.5%/drip, hard-capped at +200%) used only as a
  gentle lever toward the prestige threshold. Keep it tiny.

---

## 8. Tier-resource production sinks (kills the mid-game plateau)

Conquered **resource regions** feed CC production so deeper conquest enriches the economy
(not just unlocks more map):
- Each conquered resource region: **+3% CC production**, diminishing (×0.85 each successive one).
- Tier-4 resource regions additionally: **+5% direct CC** (non-diminishing).
- Resource ladder (per sector, ×3 faster each): T1 Sun/Melange → T2 fleet upgrades →
  T3 upgrade tree → T4 Dark Matter generation → T5 Dark Matter (endgame).

---

## 9. Upgrade tree

Three seed branches, one of each archetype (cost ×2 per level):
- **Production multiplier** — Crystal Overclock: +10% global CC/level (base 100 CC)
- **Time saver** — Expedited Warfare: −5% war timer/level (base 250 CC)
- **Cost reducer** — Bulk Enlistment: −4% Red Pill/Mech-Bro per level (base 200 CC)

Always something affordable → idle loop never deadlocks. Later: gate higher tiers behind
Abdication Stamps / Dark Matter.

---

## 10. Prestige (Abdication)

- **Story:** the bureaucratic apparatus collapses without its sovereign → automation zeroes out.
  Planets remain (territory is permanent) but come back **dormant** (produce at 0.25× until
  the economy re-ramps).
- **On prestige, RESET:** CC, generators, Red Pill, Visas, research, upgrade tree, fleet.
- **KEEP (permanent):** conquered territory (dormant), Abdication Stamps, faction vassals,
  and a **permanent fleet-range bonus (+1 reachable tier per prestige, capped at +2)**.
- **Buff:** `prestigeMult = (1 + firstBuff)^prestigeCount × (1 + stampBuff × log10(stamps + 1))`.
  The compounding `(1.5)^n` floor guarantees each run beats the last (no death-spiral); the
  `log10` stamp term keeps it bounded (a linear stamp buff caused a +6,478× runaway). Validated
  mults: ~2.5× / ~5.3× / ~14× for prestige 1 / 2 / 3.
- **HARD GATE (resolved):** range is capped at `baseReach(3) + permRangeBonus`. First run reaches
  **tier 3 only** → you wall at ~32/54 and MUST prestige to go deeper. P1 → tier 4, P2 → tier 5
  (Fringe). Ships grant their hull range but cannot exceed this prestige-driven cap.
- **Validated cadence:** P1 ≈ day 5 (walls 32/54), P2 ≈ day 11, full 54/54 ≈ day 33. The deepest
  Fringe capital (~84k army) is the climactic armada boss — a 2–3 prestige goal.
- Stamps earned per prestige: `floor((lifetime_CC / 1e9) ^ 0.5)` (divisor raised 20,000× from
  50k for the compound economy, which mints quadrillions of lifetime CC).

> ✅ RESOLVED (was the #1 open balance item): prestige is now a HARD GATE via prestige-gated
> range, not a soft accelerator. Combined with PARALLEL WARS (concurrent conquests bounded by
> uncommitted fleet capacity), the first wall bites ~day 5 at 32/54. See `docs/v0.2/BALANCE.md` §4 & §8–9.

---

## 11. Suggested data shape (JS)

Keep all tunable numbers in one config object (mirrors the spreadsheet's Assumptions sheet),
separate from runtime state. Example skeleton:

```js
const CONFIG = {
  tickRate: 1,
  offline: { capHours: 8, efficiency: 0.5 },
  generators: [
    { id: "formsworth", tier: 1, produces: "cc",          rate: 1.0,      baseCost: 40,            costMult: 1.25, unlock: { type: "start" } },
    { id: "subclerk",   tier: 2, produces: "formsworth",  rate: 0.0005,   baseCost: 800,           costMult: 1.25, unlock: { type: "cc", amount: 5000 } },
    { id: "datastack",  tier: 3, produces: "subclerk",    rate: 0.0004,   baseCost: 60000,         costMult: 1.25, unlock: { type: "cc", amount: 500000 } },
    { id: "archive",    tier: 4, produces: "datastack",   rate: 0.00032,  baseCost: 9e6,           costMult: 1.25, unlock: { type: "conquerSector", sector: "inner" } },
    { id: "sphere",     tier: 5, produces: "archive",     rate: 0.000256, baseCost: 1.6e9,         costMult: 1.25, unlock: { type: "conquerSector", sector: "mid" } },
    { id: "census",     tier: 6, produces: "sphere",      rate: 0.000205, baseCost: 3.2e11,        costMult: 1.25, unlock: { type: "conquerSector", sector: "outer" } },
    { id: "ledger",     tier: 7, produces: "census",      rate: 0.000164, baseCost: 7.2e13,        costMult: 1.25, unlock: { type: "conquerSector", sector: "fringe" } },
  ],
  ships: [
    { id: "shuttle",     researchCC: 0,    researchHrs: 0,  resGate: 0, visaCost: 1000,   capacity: 5,    range: 1 },
    { id: "frigate",     researchCC: 5e4,  researchHrs: 4,  resGate: 0, visaCost: 6000,   capacity: 30,   range: 2 },
    { id: "cruiser",     researchCC: 5e5,  researchHrs: 10, resGate: 2, visaCost: 30000,  capacity: 120,  range: 3 },
    { id: "dreadnought", researchCC: 5e6,  researchHrs: 24, resGate: 3, visaCost: 150000, capacity: 400,  range: 4 },
    { id: "leviathan",   researchCC: 5e7,  researchHrs: 48, resGate: 4, visaCost: 6e5,    capacity: 1200, range: 5 },
  ],
  war: { baseTimerHrs: 6, redPillPerMechBro: 25, tierCostScale: 4, tierTimerScale: 1.5,
         mechBase: 8, mechTierScale: 5, capitalBaseMult: 5, capitalMultPerTier: 1.5,
         parallelWars: true },
  visa: { ccPerVisa: 100 },
  sun:  { buffPerLink: 0.03, maxLinks: 3, supplyLineBonus: 0.05, globalBoostPerDrip: 0.005 },
  redpill: { primerRate: 0.00002, primerCap: 2.0, regionDropT1: 2.0, tierScale: 3.0, resourceRegionMod: 0.4 },
  prestige: { firstBuff: 0.5, stampBuff: 0.6, divisor: 1e9, curvePower: 0.5,
              dormantRate: 0.25, permRangePerPrestige: 1, permRangeCap: 2, baseReach: 3 },
  upgrades: { costGrowth: 2.0,
    branches: [
      { id: "crystalOverclock", effectPerLvl: 0.10, baseCost: 100 },
      { id: "expeditedWarfare", effectPerLvl: 0.05, baseCost: 250 },
      { id: "bulkEnlistment",   effectPerLvl: 0.04, baseCost: 200 },
    ] },
  resourceSinks: { prodBonusPerRegion: 0.03, prodDiminish: 0.85, tier4CCMult: 0.05 },
};

// runtime state (the part prestige resets vs keeps)
const STATE = {
  cc: 0, lifetimeCC: 0, redPill: 0, visas: 0, sun: 0,
  genCounts: {},          // id -> float count
  shipCounts: {},         // id -> int count (additive fleet)
  researched: ["shuttle"],
  upgLevels: {},
  conquered: [],          // region ids (PERSISTS through prestige, dormant)
  // permanent / prestige-surviving:
  stamps: 0, prestigeCount: 0, prestigeMult: 1.0, permRangeBonus: 0, factionVassals: 0,
};
```

CC/s computation (mirror of the sim):
```js
ccPerSec = genCounts.formsworth * formsworthRate
         * (1 + min(sun * globalBoostPerDrip, 2.0))      // tiny global sun lever
         * (1 + sumUpgradeProdLevels * 0.10)             // upgrade tree
         * resourceProductionMult()                       // tier-resource sinks (diminishing)
         * (1 + factionVassals * 0.25)                    // faction reward vassals
         * prestigeMult;  // (1+firstBuff)^prestigeCount * (1 + stampBuff*log10(stamps+1))
```

---

## 12. Visual direction

Two mockup styles exist (Gemini-generated). Recommended: the **amber CRT / retro-terminal**
"bureaucratic mainframe" aesthetic — it's the perfect visual pun for a bureaucracy game and is
far cheaper for a solo dev to execute consistently (typography + shaders + vector lines vs.
commissioned art). The neon-cyan glossy style is the alternative. The mockups already correctly
visualize: galaxy map with node connections + per-node yield, the CAP 3/3 link cap, +5% supply
line, sector color-coding, and the "X Mech-Bros, Y Visas" dual conquest gate.

---

## 13. Build order (suggested)

1. Compound generator chain + CC + manual tap + first automation (the 30-second hook). MVP core.
2. Generator unlock gating (CC milestones).
3. Upgrade tree (keeps early loop alive).
4. War loop: galaxy map, regions, Mech-Bros, Red Pill (hybrid), conquest timers.
5. Fleet: research → build → additive capacity + range gates. Generator unlocks via conquest.
6. Sun Drips local connection buff + tier-resource production sinks.
7. Factions + capitals (boss regions, faction vassal rewards).
8. Prestige (Abdication): reset/keep logic, dormant territory, permanent range, stamps.
9. Dark Matter endgame, offline accrual, rewarded-ad hooks (2× offline / skip timer).
10. AdMob, ASO, soft launch.

---

## Code Rules

- All numeric constants in [`docs/v0.2/BALANCE.md`](docs/v0.2/BALANCE.md), never hardcode in logic
- One render() function updates all DOM — never update DOM outside render()
- Comments in English
- Each new feature: add to state object first, then logic, then render
- No external libraries inside `assets/game.html`
- Mobile-first: touch targets minimum 44px, no hover-only interactions
- Keep single-file architecture for the game (`assets/game.html`) until v0.3
- When you change a number: change it in [`docs/v0.2/BALANCE.md`](docs/v0.2/BALANCE.md) first, re-run
  `design/economy-model/playthrough_sim.py`, confirm pacing, THEN port to the JS `CONFIG`

## What NOT To Do

- Don't add frameworks (React, Vue etc.) inside `assets/game.html`
- Don't split game logic into multiple files yet
- Don't implement prestige system yet (v0.3)
- Don't add sound yet
- Don't add images/sprites yet (placeholders only)
- Don't change the war timer base without re-running the sim — pacing is calibrated to 6h
- Never glorify or praise Mech-Bros
- Don't touch `design/economy-model/` files — they are the source of truth, not implementation targets
