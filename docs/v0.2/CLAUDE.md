# Galactic Bureaucracy — Claude Code Context

## Project Overview
A mobile-first idle/incremental game built in HTML/CSS/JS.
Sci-fi parody universe: Dune + Star Wars references, absurd bureaucratic comedy.
Player is a Galactic Emperor. Vassals are absurd bureaucrats who automate production.
Design philosophy: "Take the fun part of Stellaris, remove the boring part."
- Something grows in the first 30 seconds
- No grind, only momentum
- ADHD-first design: fast satisfaction, early hook
- Waiting time is not punishment — it's a reason to return

## Tech Stack
- Pure HTML/CSS/JS (single file: prototype.html)
- No frameworks, no build step
- Target: mobile browser + Capacitor/PWA for store release
- Stable Diffusion for assets (added later)

## File Structure
```
prototype.html     ← entire game, single file
CLAUDE.md          ← this file
BALANCE.md         ← all numeric constants
docs/GDD.md        ← design decisions and lore
```

## Core Architecture

### State Object
All game state lives in a single `state` object:
```js
state = {
  // Resources
  crystal, sun, pepper, redpill, mechBros,
  darkMatter, abdicationStamps,

  // Meta
  totalEarned, clicks, startTime,
  firstDimensionAt, firstConquestAt,

  // Dimensions (NEW - Antimatter Dimensions style)
  dimensions: [
    { tier: 1, owned: 0, purchased: 0, baseCost: 10, costMult: 1000, baseProduction: 1 },
    { tier: 2, owned: 0, purchased: 0, baseCost: 100, costMult: 10000, ... },
    // ... up to tier 8
  ],

  // Vassals
  vassals: { formsworth, brglx, zyx, vrrk, hrManager, archivist },

  // Map
  regions: [...],
  selectedRegion: null,
  activeWars: [],
  baseWarHours: 8,
}
```

### Tick Loop
```js
requestAnimationFrame(tick)
// Each tick: dt = time since last tick in seconds
// production = rate * dt added to resources
// checkWarsComplete()
// render()
```

### Render Pattern
One render() function updates all DOM. Never update DOM outside render().
Use fmt() for all number display.

## Dimension System (Antimatter Dimensions Style)

This is the CORE idle mechanic. Replace/extend the current Formsworth-only production.

### How It Works
- 8 Dimension tiers total
- Tier 1 produces Cyber Crystal
- Tier 2 produces Tier 1 Dimensions
- Tier 3 produces Tier 2 Dimensions
- ... and so on (each tier produces the tier below it)
- This creates exponential compound growth

### Multiplier System
- Each dimension has a multiplier (starts at ×1.0)
- Every 10 purchased of that dimension: multiplier ×2
- Price increases each time multiplier upgrades
- Show: [purchased toward next 10] in brackets like AD

### Buy Modes
- Buy 1: buy single unit
- Buy Until 10: buy up to next multiplier threshold
- Max All: buy Until 10 on each dimension from 1→8 in sequence

### Dimension Names (Galactic Bureaucracy flavor)
```
Tier 1: Imperial Scriv        — produces Crystal
Tier 2: Sector Clerk          — produces Tier 1
Tier 3: Regional Overseer     — produces Tier 2
Tier 4: Star Consul           — produces Tier 3
Tier 5: Void Prefect          — produces Tier 4
Tier 6: Galactic Auditor      — produces Tier 5
Tier 7: Dimensional Envoy     — produces Tier 6
Tier 8: The Bureaucrat Supreme — produces Tier 7
```

### Flavor texts (shown under each dimension name)
```
Tier 1: "Fills out forms. Produces crystal. Sometimes the right form."
Tier 2: "Manages the Scrivs. Has never met one."
Tier 3: "Oversees 12 sectors. Knows the name of 0."
Tier 4: "A consul of stars. Stapler missing since 3042."
Tier 5: "Prefect of the void. The void prefects back."
Tier 6: "Audits the galaxy. The galaxy owes 4 forms."
Tier 7: "Envoy between dimensions. Lost the return memo."
Tier 8: "Supreme. The form IS the bureaucrat now."
```

### Base Prices (from Antimatter Dimensions)
```
Tier 1: 10
Tier 2: 100
Tier 3: 10,000
Tier 4: 1,000,000
Tier 5: 1,000,000,000
Tier 6: 10,000,000,000,000
Tier 7: 1,000,000,000,000,000
Tier 8: 1,000,000,000,000,000,000
```

### Price increase per 10 bought
```
Tier 1: ×1,000
Tier 2: ×10,000
Tier 3: ×100,000
Tier 4: ×1,000,000
Tier 5: ×100,000,000
Tier 6: ×10,000,000,000
Tier 7: ×1,000,000,000,000
Tier 8: ×1,000,000,000,000,000
```

## Currency System

### Production Currencies
| Currency | Symbol | Source | Spent On |
|---|---|---|---|
| Cyber Crystal | ◆ | Dimension Tier 1 + ticking | Dimensions, vassals, Red Pill conversion |
| Sun Drips | ☀️ | Sun regions + Brglx vassal | (v0.3) production multiplier upgrades |
| Pepper Melange | 🌶️ | Pepper regions + Zyx vassal | (v0.3) cost-discount upgrades |
| Red Pill | 💊 | 100 Crystal → 1 Red Pill | Mech-Bro enlistment |
| Dark Matter | ◈ | Mid-game unlock (conquest milestones) | Vassal re-roll / permanent stat upgrades |
| Abdication Stamp | 📜 | Prestige currency | Carry-over buffs on new universe reset |

### Mech-Bro
- 5 Red Pill → 1 Mech-Bro
- 3 Mech-Bros required per war
- Visual/flavor: "Pimply teenager in a mech suit." — intentionally disposable, never glorified

## Vassal System

Vassals are purchased and upgraded. Without them production is manual.
With them: automation. This transition is the main dopamine moment.

### Vassal Buff Types
- Passive production multiplier
- Special ability (timer reduction etc.)
- Unlock gate for next content

### Vassal Roster
```
Lord Formsworth III
  Flavor: "Has been filling out the same form for 40 years. Still not approved."
  Buff: Crystal production +12% per level
  Base cost: 50 ◆
  Unlock: always available

Sun Scraper Brglx
  Flavor: "Hanging from the north pole of the sun by a rope. Sweating. Has complaints."
  Visual note: person dangling from rope on sun like a window cleaner
  Buff: Automates Sun Drips production (+1.0 ☀️/sn per level)
  Base cost: 500 ◆
  Unlock: 10 Formsworth purchased + 1 Sun region owned

Pepper Minister Zyx
  Flavor: "Doesn't know what Pepper Melange is. Has the ministry anyway."
  Buff: Pepper +20% multiplier per level (self-compound), region harvest automation
  Base cost: 5,000 ◆
  Unlock: 1 Pepper region owned

Drood Commander Vrrk
  Flavor: "Says he's not a Drood. He is a Drood."
  Buff: War timer -1h per level (max -3h)
  Base cost: 2,500 ◆
  Unlock: After first conquest

Galactic HR Director
  Flavor: "Regulating Mech-Bro labor rights. Failing."
  Buff: Red Pill conversion cost -15%
  Base cost: 8,000 ◆
  Unlock: 3 Mech-Bros enlisted total

Abdication Archivist
  Flavor: "Documents every prestige. Has cried at each one."
  Buff: Abdication Stamp +1 bonus on prestige
  Base cost: 15,000 ◆
  Unlock: First prestige completed
```

## Map System (Conquest Loop)

Risk-board visual. 8 regions. Borders define attack eligibility.

### Regions
```
Kerebros-7 (Home/Crystal)   — player start, connects: sun1, pepper1, npc1
Brglx Heights (Sun)         — enemy, connects: home, sun2, pepper1
Helios IX (Sun)             — enemy, connects: sun1, pepper1
Korol Star-Glare (Sun)      — enemy, connects: sun2, pepper2
Pulchritudia (Pepper)       — enemy, connects: home, sun1, npc1
Melange Protrusion (Pepper) — enemy, connects: home, pepper1, sun3, npc1
Zyxworld (Pepper)           — enemy, connects: pepper2, sun3
Drood Federation (NPC Capital) — enemy, connects: pepper1, pepper2
```

### Attack Rules
- Must have adjacent player-owned region to attack
- Costs 3 Mech-Bros
- War timer: 8h base (Vrrk reduces by 1h/level, max -3h)
- On completion: region becomes player-owned, yields resource/sec
- Base yield: Sun regions → 0.5 ☀️/sn, Pepper regions → 0.5 🌶️/sn

### NPC Names (for flavor)
Drood Federation, Hexagonal Council, The Seven Thousand Bureaucrats Conclave, Anaerobic Congress

## Prestige System (Abdication)

When empire stalls → player abdicates → new universe → starts stronger.

```
Empire slows → Abdication Stamp accumulates → 
Player hits "Abdicate" → New Universe begins →
Stamps carry over as permanent buffs
```

Notification: "Abdication Form approved. Proceed to Universe 2."
Dark Matter: earned through mid-game milestones, used for vassal re-rolls (permanent progression without prestige)

## Loops

### Production Loop
Dimensions → Crystal → buy more Dimensions → exponential growth

### Expansion Loop  
Crystal → Vassals → automation → faster Crystal → more Vassals

### Conquest Loop
Crystal → Red Pill → Mech-Bro → War Timer (8h) → New Region → Sun/Pepper income

### Prestige Loop
Empire stalls → Abdication Stamp → New Universe → Stronger start

## UI Structure

### Tabs
1. Empire (idle/dimensions tab)
2. Map (conquest)
3. War (Red Pill, Mech-Bro, active wars)
4. Vassals (buy/upgrade vassals)

### Resource Bar (always visible, top)
◆ Crystal | ☀️ Sun | 🌶️ Pepper | 💊 Red Pill
(locked/dimmed until unlocked)

### Empire Tab Layout
- Resource rates summary
- Dimension grid (8 rows)
  - Each row: [Name + flavor] [×multiplier] [owned (purchased)] [growth%] [Buy 1] [Until 10]
  - Bottom: [Max All] button
- Tickspeed upgrade (bonus production speed, purchasable)

## Formatting & Display

```js
function fmt(n) {
  // Show decimals only for small numbers
  if (n >= 1e9)  return (n/1e9).toFixed(2) + 'B';
  if (n >= 1e6)  return (n/1e6).toFixed(2) + 'M';
  if (n >= 1e3)  return (n/1e3).toFixed(1) + 'K';
  if (n >= 10)   return Math.floor(n).toString();
  return n.toFixed(1);
}
// For very large numbers later: add T, Qt, Sp, Oc, No, Dc notation
```

## Code Rules
- All numeric constants in BALANCE.md, never hardcode in logic
- Never update DOM outside render()
- Comments in English
- Each new feature: add to state object first, then logic, then render
- No external libraries
- Mobile-first: touch targets minimum 44px, no hover-only interactions
- Keep single file architecture until v0.3

## What NOT To Do
- Don't add frameworks (React, Vue etc.)
- Don't split into multiple files yet
- Don't implement prestige system yet (v0.3)
- Don't add sound yet
- Don't add images/sprites yet (placeholders only)
- Don't change the war timer base (8h) — this is a design decision
- Never glorify or praise Mech-Bros
