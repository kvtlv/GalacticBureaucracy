# Galactic Bureaucracy — Balance Constants
All numeric game constants live here. Claude Code reads this before changing any numbers.
Last updated: v0.2

---

## Dimension System

### Base Costs (Crystal)
```
DIMENSION_BASE_COST = [
  10,                    // Tier 1: Imperial Scriv
  100,                   // Tier 2: Sector Clerk
  10_000,                // Tier 3: Regional Overseer
  1_000_000,             // Tier 4: Star Consul
  1_000_000_000,         // Tier 5: Void Prefect
  10_000_000_000_000,    // Tier 6: Galactic Auditor
  1e15,                  // Tier 7: Dimensional Envoy
  1e18,                  // Tier 8: The Bureaucrat Supreme
]
```

### Price Multiplier Per 10 Bought
```
DIMENSION_COST_MULT = [
  1_000,                 // Tier 1
  10_000,                // Tier 2
  100_000,               // Tier 3
  1_000_000,             // Tier 4
  100_000_000,           // Tier 5
  10_000_000_000,        // Tier 6
  1_000_000_000_000,     // Tier 7
  1e15,                  // Tier 8
]
```

### Base Production Per Dimension Per Second
```
DIMENSION_BASE_PROD = [
  1,    // Tier 1 → produces 1 Crystal/sec each
  1,    // Tier 2 → produces 1 Tier-1/sec each
  1,    // Tier 3 → produces 1 Tier-2/sec each
  1,    // Tier 4 → produces 1 Tier-3/sec each
  1,    // Tier 5 → produces 1 Tier-4/sec each
  1,    // Tier 6 → produces 1 Tier-5/sec each
  1,    // Tier 7 → produces 1 Tier-6/sec each
  1,    // Tier 8 → produces 1 Tier-7/sec each
]
// Note: actual production = owned × base × multiplier
// Multiplier starts at 1.0, doubles every 10 purchased
```

### Dimension Multiplier
```
DIMENSION_MULTIPLIER_BASE = 1.0       // starting multiplier for all tiers
DIMENSION_MULTIPLIER_STEP = 2.0       // ×2 every 10 purchased
DIMENSION_MULTIPLIER_THRESHOLD = 10   // purchased count trigger
```

---

## Vassal System

### Lord Formsworth III
```
FORMSWORTH_BASE_COST = 50
FORMSWORTH_COST_MULT = 1.15       // price × 1.15 per purchase
FORMSWORTH_BUFF_CRYSTAL = 0.12    // +12% Crystal production per level
FORMSWORTH_UNLOCK = always
```

### Sun Scraper Brglx
```
BRGLX_BASE_COST = 500
BRGLX_COST_MULT = 1.15
BRGLX_SUN_PRODUCTION = 1.0        // ☀️/sec per level
BRGLX_UNLOCK_FORMSWORTH = 10      // requires 10 Formsworth
BRGLX_UNLOCK_SUN_REGIONS = 1      // requires 1 owned Sun region
```

### Pepper Minister Zyx
```
ZYX_BASE_COST = 5000
ZYX_COST_MULT = 1.18
ZYX_PEPPER_BASE_PROD = 0.5        // 🌶️/sec per level (before compound)
ZYX_SELF_COMPOUND = 0.20          // each Zyx adds +20% to all previous Zyxes
ZYX_UNLOCK_PEPPER_REGIONS = 1     // requires 1 owned Pepper region
```

### Drood Commander Vrrk
```
VRRK_BASE_COST = 2500
VRRK_COST_MULT = 1.20
VRRK_WAR_REDUCTION_PER_LEVEL = 1  // hours reduced per level
VRRK_WAR_REDUCTION_MAX = 3        // maximum total reduction (hours)
VRRK_UNLOCK = first_conquest      // unlocks after winning first war
```

### Galactic HR Director
```
HR_BASE_COST = 8000
HR_COST_MULT = 1.18
HR_REDPILL_DISCOUNT = 0.15        // Red Pill conversion -15% cost
HR_UNLOCK_MECHS = 3               // requires 3 total Mech-Bros enlisted
```

### Abdication Archivist
```
ARCHIVIST_BASE_COST = 15000
ARCHIVIST_COST_MULT = 1.20
ARCHIVIST_STAMP_BONUS = 1         // +1 Abdication Stamp per prestige
ARCHIVIST_UNLOCK = first_prestige // unlocks after first abdication
```

---

## Combat / War System

```
WAR_BASE_DURATION_HOURS = 8       // base war timer
WAR_MIN_DURATION_HOURS = 2        // floor (even with max Vrrk)
WAR_MECHS_REQUIRED = 3            // Mech-Bros consumed per war
WAR_MAX_SIMULTANEOUS = 3          // parallel wars allowed
```

---

## Currency Conversion

```
CRYSTAL_TO_REDPILL_RATE = 100     // 100 Crystal → 1 Red Pill
REDPILL_TO_MECH_RATE = 5          // 5 Red Pills → 1 Mech-Bro
```

---

## Map / Region System

```
REGION_SUN_BASE_YIELD = 0.5       // ☀️/sec per owned Sun region
REGION_PEPPER_BASE_YIELD = 0.5    // 🌶️/sec per owned Pepper region
REGION_COUNT_TOTAL = 8
REGION_COUNT_SUN = 3
REGION_COUNT_PEPPER = 3
REGION_COUNT_NPC_CAPITAL = 1
REGION_COUNT_HOME = 1
```

---

## Dark Matter (Mid-Game)

```
DARK_MATTER_UNLOCK = conquest_milestone_3   // unlocks after 3 regions conquered
DARK_MATTER_VASSAL_REROLL_COST = 10         // DM cost to reroll a vassal stat
DARK_MATTER_PRODUCTION = 0                  // not auto-produced, milestone rewards only
```

---

## Prestige / Abdication

```
ABDICATION_STAMP_BASE_BUFF = 0.02     // each stamp = +2% permanent production
ABDICATION_STAMP_MAX_STACKS = 100     // cap at 100 stamps (200% total bonus)
ABDICATION_TRIGGER = manual           // player manually abdicates, no auto-trigger
```

---

## Timing & Feel

```
TICK_RATE = requestAnimationFrame     // ~60fps
FIRST_DIMENSION_TARGET_SECONDS = 8   // player should buy first dim within 8s
HOOK_WINDOW_SECONDS = 30              // something must grow in first 30s
```

---

## Simulation Results (v0.2, from sim_v02.py)

Engaged player (4 clicks/sec, 24h):
- 6s: First Tier-1 Dimension purchased ← hook confirmed
- 59s: 10 Dimensions owned
- 2m46s: First war initiated (Sun target)
- 8h02: First Sun region conquered
- 16h02: First Pepper region conquered
- 24h: 4.4M Crystal, 1.18M Sun, 14K Pepper, 2 regions owned

Casual player (1 click/sec, 24h):
- 24s: First Dimension purchased ← still within 30s hook window
- Subsequent tempo nearly identical (automation equalizes)

Key finding: Engaged vs casual gap is minimal after first dimension.
ADHD-first principle confirmed — no pressure to click constantly.

---

## Open Balance Questions

| Question | Status |
|---|---|
| Sun/Pepper spending routes | Not implemented yet — v0.3 upgrade trees |
| Dark Matter exact milestone triggers | TBD |
| Tickspeed upgrade costs | TBD — add when dimension system stable |
| NPC Capital conquest reward | TBD — large one-time Crystal burst? |
| Prestige carry-over exact formula | TBD — v0.3 |
