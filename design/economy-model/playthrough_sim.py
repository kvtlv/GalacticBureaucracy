#!/usr/bin/env python3
"""
Galactic Bureaucracy — Playthrough Simulator
Plays the game forward tick-by-tick over N days using a realistic player schedule.
Reads ALL balance knobs live from galactic_bureaucracy_economy.xlsx, so tuning the
sheet and re-running closes the feedback loop. Outputs a CSV log + a milestone report
+ flags where progression stalls or runs away.
"""
import csv, json, math, sys
from openpyxl import load_workbook

XLSX = "galactic_bureaucracy_economy.xlsx"

# ---------- read assumptions live from the sheet ----------
def load_assumptions(path=XLSX):
    wb = load_workbook(path, data_only=True)
    wa = wb["Assumptions"]
    A = {}
    for r in range(4, 92):
        p = wa.cell(row=r, column=2).value
        v = wa.cell(row=r, column=3).value
        if isinstance(p, str) and isinstance(v, (int, float)):
            A[p] = v
    # vassal Formsworth (CC engine) base cost/mult/output
    wv = wb["Vassals"]
    A["_formsworth_base"]  = wv.cell(row=5, column=3).value
    A["_formsworth_mult"]  = wv.cell(row=5, column=4).value
    A["_formsworth_out"]   = wv.cell(row=5, column=6).value
    # fleet: shuttle visa cost + capacity
    wf = wb["Fleet_Sim"]
    A["_shuttle_cap"]  = wf.cell(row=6, column=3).value
    A["_shuttle_visa"] = wf.cell(row=6, column=4).value
    A["_frigate_cap"]  = wf.cell(row=7, column=3).value
    A["_frigate_visa"] = wf.cell(row=7, column=4).value
    A["_cruiser_cap"]  = wf.cell(row=8, column=3).value
    A["_cruiser_visa"] = wf.cell(row=8, column=4).value
    # CC generator COMPOUND chain: each tier produces the tier below; only tier 1 mints CC
    wg = wb["CC_Generators"]
    gens = []
    unlock_map = {"start":"start","CC 5k":("cc",5000),"CC 500k":("cc",500000),
                  "conquer Inner":("tier",2),"conquer Mid":("tier",3),
                  "conquer Outer":("tier",4),"conquer Fringe":("tier",5)}
    # rows 6-12: name(B), tier(C), produces(D), base_rate(E), base_cost(F), unlock(G)
    for r in range(6, 13):
        name = wg.cell(row=r, column=2).value
        if not name: continue
        gens.append({
            "name": name,
            "tier": wg.cell(row=r, column=3).value,
            "rate": wg.cell(row=r, column=5).value,     # units of tier-below per sec (tier1: CC/sec)
            "base_cost": wg.cell(row=r, column=6).value,
            "unlock": unlock_map.get(wg.cell(row=r, column=7).value, "start"),
        })
    # cost mults live in a small block below (col B name, col C mult), find them
    mults = {}
    for r in range(14, 40):
        nm = wg.cell(row=r, column=2).value
        mv = wg.cell(row=r, column=3).value
        if nm and isinstance(mv, (int, float)):
            mults[nm] = mv
    for g in gens:
        g["mult"] = mults.get(g["name"], 1.12)
    A["_generators"] = gens
    return A

# ---------- player schedule ----------
# realistic ADHD-first cadence: several short check-ins per day with offline gaps between.
# returns list of (active_seconds, offline_seconds_before_this_session)
def build_schedule(days, sessions_per_day=4, session_min=5):
    sched = []
    sec_session = session_min * 60
    # day = 86400s; spread sessions, offline = gap between them
    gap = 86400 // sessions_per_day
    for d in range(days):
        for s in range(sessions_per_day):
            offline = gap - sec_session if (d > 0 or s > 0) else 0
            sched.append((sec_session, max(offline, 0)))
    return sched

# ---------- region generator (mirrors War_Sim structure) ----------
def build_galaxy(A):
    sectors = [("Core",1,10),("Inner",2,10),("Mid",3,10),("Outer",4,10),("Fringe",5,10)]
    rp_per   = A["Red Pill per Mech-Bro"]
    tier_cost= A["Tier cost scale"]
    tier_out = A["Tier output scale"]
    tier_tmr = A["Tier timer scale"]
    base_tmr = A["Base war timer (hrs)"]
    mech_base  = A.get("Mech-Bro base (tier1)", 8.0)
    mech_scale = A.get("Mech-Bro tier scale", 5.0)
    cap_base_mult = A.get("Capital army base mult", 5.0)
    cap_per_tier = A.get("Capital mult per tier", 1.5)
    regions = []
    for sname, tier, n in sectors:
        sector_regions = []
        for i in range(n):
            # exponential by tier, mild linear ramp within sector
            mech = int(round(mech_base * (mech_scale ** (tier-1)) * (1 + 0.1*i)))
            rp_cost = mech * rp_per * (tier_cost ** (tier-1))
            timer_h = max(base_tmr * (tier_tmr ** (tier-1)), 1)
            out = (mech * 0.4) * (tier_out ** (tier-1))
            is_resource = (i % 2 == 0)
            reg = {
                "name": f"{sname[:3]}-{i+1:02d}", "sector": sname, "tier": tier,
                "mech": mech, "rp_cost": rp_cost, "timer_s": timer_h*3600, "out": out,
                "resource_type": is_resource, "is_capital": False,
            }
            sector_regions.append(reg)
        # faction capital for tiers 2+ (Core is tutorial/unowned). Capital = boss region.
        if tier >= 2:
            normal_mech = mech_base * (mech_scale ** (tier-1))
            cap_mult = cap_base_mult * (cap_per_tier ** (tier-2))  # Inner=5x ... Fringe~25x
            cap_mech = int(round(normal_mech * cap_mult))
            cap_timer = max(base_tmr * (tier_tmr ** (tier-1)) * 2, 1)  # capitals take longer
            sector_regions.append({
                "name": f"{sname[:3]}-CAPITAL", "sector": sname, "tier": tier,
                "mech": cap_mech, "rp_cost": cap_mech * rp_per * (tier_cost ** (tier-1)),
                "timer_s": cap_timer*3600, "out": (normal_mech*0.4)*(tier_out**(tier-1))*2,
                "resource_type": False, "is_capital": True, "cap_mult": round(cap_mult,1),
            })
        regions.extend(sector_regions)
    return regions

# ---------- the simulation ----------
def simulate(days=14, verbose=False):
    A = load_assumptions()
    cc = 0.0
    lifetime_cc = 0.0
    red_pill = 0.0
    visas = 0.0
    sun = 0.0
    melange = 0.0
    formsworth = 0
    fleet_cap = 0          # current best ship capacity
    owned_ships = []
    conquered = []
    upg_prod_lvl = 0        # Crystal Overclock levels

    fb = A["_formsworth_base"]; fm = A["_formsworth_mult"]; fo = A["_formsworth_out"]
    click_yield = A["Manual click yield"]
    offline_eff = A["Offline efficiency"]
    offline_cap_s = A["Offline cap"] * 3600
    cc_per_visa = A["CC per Transit Visa"]
    sun_boost = A["Sun Drips -> CC boost"]
    rp_per = A["Red Pill per Mech-Bro"]
    upg_growth = A["Upgrade cost growth"]
    rate_step = A["Resource rate step"]

    # prestige / research knobs
    FIRST_PRESTIGE_BUFF = A["First-prestige buff"]   # 1.0 == +100% (2x)
    DORMANT_RATE = A["Dormant territory rate"]
    RESEARCH_SPEED = A["Research speed mult"]
    STAMP_BUFF = A["Stamp buff per stamp"]
    PRESTIGE_DIV = A["Prestige divisor"]
    PRESTIGE_POW = A["Prestige curve power"]

    # ship models: (name, research_cc, research_hours, resource_tier_gate, build_visas, capacity, range_tier)
    # smaller ships = better Visa-per-capacity, but limited RANGE (max tier they can reach).
    SHIP_MODELS = [
        ("Shuttle",     0,        0,  0, 1000,   5,    1),   # 200 visa/cap — cheapest per bro, reaches tier 1
        ("Frigate",     50000,    4,  0, 6000,   30,   2),   # 200 visa/cap, range 2
        ("Cruiser",     500000,   10, 2, 30000,  120,  3),   # 250 visa/cap, range 3
        ("Dreadnought", 5000000,  24, 3, 150000, 400,  4),   # 375 visa/cap, range 4
        ("Leviathan",   50000000, 48, 4, 600000, 1200, 5),   # 500 visa/cap — priciest per bro, reaches tier 5
    ]

    # Red Pill economy (hybrid): CC primer trickle + tier-scaled region drops
    RP_PRIMER = A["CC->Red Pill primer rate"]        # RP per (CC/sec)
    RP_REGION_T1 = A["Region Red Pill drop (tier1)"] # RP/s per conquered tier-1 region
    RP_TIER_SCALE = A["Red Pill tier scale"]         # deeper regions pay more
    RP_RESOURCE_MOD = A["Resource-region RP modifier"]  # Sun/Melange regions pay this fraction
    RP_PRIMER_CAP = A.get("Red Pill primer cap", 2.0)    # absolute ceiling on primer RP/s (bootstrap only)

    galaxy = build_galaxy(A)
    war_unlock_lifetime = 1_000_000   # from earlier decision: war unlocks ~1M lifetime CC

    schedule = build_schedule(days)
    t = 0
    log = []
    milestones = {}

    # mutable state that prestige partially resets
    state = {
        "cc": cc, "lifetime_cc": lifetime_cc, "red_pill": red_pill, "visas": visas,
        "sun": sun, "formsworth": formsworth, "fleet_cap": fleet_cap,
        "gen_counts": {},  # generator name -> count owned (multi-tier producer ladder)
        "owned_ships": owned_ships, "upg_prod_lvl": upg_prod_lvl,
        "active_wars": [], "pending_research": None,
        "researched": set(["Shuttle"]),  # shuttle is instant at war-unlock
        "ship_counts": {},   # name -> count built (additive fleet)
        "stamps": 0, "prestige_count": 0, "prestige_mult": 1.0,
        "fleet_range": 0,
        "perm_range_bonus": 0,   # permanent: each prestige +1 reachable tier (survives reset)
        "admirals": int(A.get("Starting admirals", 1)),  # concurrent-war slots; +1 per capital taken
    }
    ADMIRAL_TIER_GATE = int(A.get("Admiral capital tier gate", 0))  # capitals at tier > this also award an admiral; 0 = every capital

    def deepest_tier_conquered():
        tiers = [r["tier"] for r in galaxy if r["name"] in conquered]
        return max(tiers) if tiers else 0

    PROD_BONUS = A.get("Resource-region prod bonus", 0.03)
    PROD_DIMINISH = A.get("Prod bonus diminish", 0.85)
    TIER4_CC_MULT = A.get("Tier4 res -> CC mult", 0.05)

    def resource_production_mult():
        # each conquered RESOURCE region grants a diminishing production bonus.
        # deeper (tier-4) resource regions add a stronger direct CC multiplier.
        bonus = 0.0
        n = 0
        for reg in galaxy:
            if reg["name"] in conquered and reg.get("resource_type"):
                bonus += PROD_BONUS * (PROD_DIMINISH ** n)
                if reg["tier"] >= 4:
                    bonus += TIER4_CC_MULT  # deep resource regions: stronger, non-diminishing
                n += 1
        return 1 + bonus

    GENS = A["_generators"]
    # generators sorted by tier ascending
    GENS_BY_TIER = sorted(GENS, key=lambda g: g["tier"])
    TIER1 = GENS_BY_TIER[0]

    def gen_unlocked(g):
        u = g["unlock"]
        if u == "start": return True
        if isinstance(u, tuple):
            if u[0] == "cc": return state["lifetime_cc"] >= u[1]
            if u[0] == "tier": return deepest_tier_conquered() >= u[1]
        return False

    def advance_chain(seconds):
        # COMPOUND: top-down, each tier N produces (count_N * rate_N * seconds) units of tier N-1.
        # tier 1 produces CC (handled in step()). Higher tiers grow the counts below them.
        counts = state["gen_counts"]
        for i in range(len(GENS_BY_TIER)-1, 0, -1):   # from highest tier down to tier 2
            g = GENS_BY_TIER[i]
            below = GENS_BY_TIER[i-1]
            produced = counts.get(g["name"], 0) * g["rate"] * seconds
            if produced:
                counts[below["name"]] = counts.get(below["name"], 0) + produced

    def base_production():
        # CC/sec = tier-1 count * tier-1 rate
        return state["gen_counts"].get(TIER1["name"], 0) * TIER1["rate"]

    def cc_per_sec():
        base = base_production()
        sun_mult = 1 + min(state["sun"] * sun_boost, 2.0)
        prod_upg = 1 + state["upg_prod_lvl"] * 0.10
        res_mult = resource_production_mult()
        faction_mult = 1 + state.get("faction_vassals", 0) * 0.25
        return base * sun_mult * prod_upg * res_mult * faction_mult * state["prestige_mult"]

    def try_buy_generators():
        # buy whole units of unlocked generators. Spend greedily but keep a reserve for war/visas.
        # heuristic: buy the highest-tier unlocked generator we can afford (drives compounding),
        # then fill in cheaper ones. Cap purchases per call to avoid infinite loops.
        for _ in range(200):
            best = None
            for g in reversed(GENS_BY_TIER):
                if not gen_unlocked(g): continue
                owned = int(state["gen_counts"].get(g["name"], 0))
                # if compounding already made this tier plentiful, manual buying is irrelevant
                if owned > 500:
                    continue
                cost = g["base_cost"] * (g["mult"] ** owned)
                if state["cc"] >= cost:
                    best = (g, cost); break   # highest tier affordable
            if not best: break
            g, cost = best
            state["cc"] -= cost
            state["gen_counts"][g["name"]] = state["gen_counts"].get(g["name"], 0) + 1

    def try_buy_upgrade():
        cost = 100 * (upg_growth ** state["upg_prod_lvl"])
        if state["cc"] >= cost and state["cc"] > cost * 2.5:
            state["cc"] -= cost; state["upg_prod_lvl"] += 1

    def try_research():
        # research the next un-researched model if CC affordable, resource gate met, no research pending
        if state["pending_research"] is not None: return
        for name, rcc, rhrs, gate_tier, visa, cap, rng in SHIP_MODELS:
            if name in state["researched"]: continue
            if gate_tier > 0 and deepest_tier_conquered() < gate_tier:
                return  # gated: need deeper territory first (THE WALL)
            if state["cc"] >= rcc:
                state["cc"] -= rcc
                finish = t + rhrs*3600*RESEARCH_SPEED
                state["pending_research"] = (name, finish)
            return

    def resolve_research():
        pr = state["pending_research"]
        if pr and t >= pr[1]:
            state["researched"].add(pr[0])
            state["pending_research"] = None

    def fleet_capacity():
        total = 0
        for name, rcc, rhrs, gate_tier, visa, cap, rng in SHIP_MODELS:
            total += state["ship_counts"].get(name, 0) * cap
        return total

    def fleet_max_range():
        # A ship grants its hull range, but DEEP SPACE is gated by prestige.
        # Hard cap = BASE_REACH + perm_range_bonus. First run (0 prestige) reaches tier 3.
        # Each Abdication permanently lifts the cap by 1 tier -> prestige is the key to the Fringe.
        BASE_REACH = 3
        ship_rng = 0
        for name, rcc, rhrs, gate_tier, visa, cap, rng in SHIP_MODELS:
            if state["ship_counts"].get(name, 0) > 0:
                ship_rng = max(ship_rng, rng)
        hard_cap = BASE_REACH + state["perm_range_bonus"]
        return min(ship_rng, hard_cap)

    def try_build_ship():
        # Additive fleet: keep buying ships. Prefer the largest researched ship we can afford
        # (best capacity per Visa at scale), but always build SOMETHING if affordable.
        researched_models = [m for m in SHIP_MODELS if m[0] in state["researched"]]
        # try largest-first for efficiency at scale
        for name, rcc, rhrs, gate_tier, visa, cap, rng in reversed(researched_models):
            if state["visas"] >= visa:
                state["visas"] -= visa
                state["ship_counts"][name] = state["ship_counts"].get(name, 0) + 1
                state["fleet_cap"] = fleet_capacity()
                state["fleet_range"] = fleet_max_range()
                return

    def convert_cc_to_visas():
        # convert spare CC to visas whenever there's a researched ship and unconquered territory remains
        if state["lifetime_cc"] < war_unlock_lifetime: return
        if not any(m[0] in state["researched"] for m in SHIP_MODELS): return
        if len(conquered) >= len(galaxy): return
        spend = state["cc"] * 0.30
        gained = spend / cc_per_visa
        if gained >= 1:
            state["cc"] -= spend; state["visas"] += gained

    def committed_capacity():
        # capacity tied up in in-flight wars (each war reserves its region's army need)
        return sum(w[0]["mech"] for w in state["active_wars"])

    def try_start_war():
        if state["lifetime_cc"] < war_unlock_lifetime: return
        if state["fleet_cap"] <= 0: return
        # Two gates on simultaneous wars: (1) ADMIRALS — each admiral commands one concurrent
        # campaign (armada); (2) uncommitted fleet CAPACITY must lift the army. Admirals are the
        # binding parallel-war limit; you earn more by conquering capitals (esp. deep tier>gate ones).
        for _ in range(200):
            if len(state["active_wars"]) >= state["admirals"]: break   # no free admiral to lead a new armada
            free_cap = state["fleet_cap"] - committed_capacity()
            in_flight = {w[0]["name"] for w in state["active_wars"]}
            started = False
            for reg in galaxy:
                if reg["name"] in conquered or reg["name"] in in_flight: continue
                if reg["mech"] > free_cap: continue          # must fit in uncommitted lift
                if reg["tier"] > state["fleet_range"]: continue  # RANGE gate (prestige-gated deep space)
                if state["red_pill"] >= reg["rp_cost"]:
                    state["red_pill"] -= reg["rp_cost"]
                    state["active_wars"].append((reg, t + reg["timer_s"]))
                    started = True
                    break
            if not started: break

    def resolve_war():
        still = []
        for pw in state["active_wars"]:
            reg, finish = pw
            if t >= finish:
                conquered.append(reg["name"])
                state["sun"] += reg["out"]
                if reg.get("is_capital"):
                    # faction eliminated: a unique vassal joins -> permanent +production
                    state["faction_vassals"] = state.get("faction_vassals", 0) + 1
                    milestones.setdefault(f"faction_{reg['sector']}_defeated", t)
                    # ADMIRAL REWARD: a defeated faction's fleet commander defects to you.
                    # Every capital grants +1 admiral (+1 concurrent war). Deep capitals
                    # (tier > ADMIRAL_TIER_GATE) are the prized armada-builders.
                    if reg["tier"] > ADMIRAL_TIER_GATE:
                        state["admirals"] += 1
                        state["perm_admirals"] = state.get("perm_admirals", 0) + 1
                        milestones.setdefault(f"admiral_{state['perm_admirals']}", t)
                milestones.setdefault(f"conquer_{len(conquered)}", t)
            else:
                still.append(pw)
        state["active_wars"] = still

    def region_red_pill_per_sec():
        total = 0.0
        for reg in galaxy:
            if reg["name"] in conquered:
                base = RP_REGION_T1 * (RP_TIER_SCALE ** (reg["tier"] - 1))
                if reg.get("resource_type"):
                    base *= RP_RESOURCE_MOD
                total += base
        return total

    def can_progress():
        # is there ANY unconquered region the current fleet can both lift AND reach?
        for reg in galaxy:
            if reg["name"] not in conquered and reg["mech"] <= state["fleet_cap"] and reg["tier"] <= state["fleet_range"]:
                return True
        return False

    def next_ship_blocked_by_wall():
        # is the next ship research gated behind territory we can't yet reach?
        for name, rcc, rhrs, gate_tier, visa, cap, rng in SHIP_MODELS:
            if name in state["researched"]: continue
            return gate_tier > 0 and deepest_tier_conquered() < gate_tier
        return False

    def do_prestige():
        # PRESTIGE: reset economy, KEEP territory (dormant), grant stamp buff
        lt = state["lifetime_cc"]
        new_stamps = int((lt / PRESTIGE_DIV) ** PRESTIGE_POW)
        state["stamps"] += max(new_stamps, 1)
        state["prestige_count"] += 1
        # Buff must OUTPACE the reset, or prestige is a death spiral. Two stacking parts:
        #  (1) a per-prestige floor (FIRST_PRESTIGE_BUFF compounded) guaranteeing each run is
        #      stronger than the last regardless of stamps;
        #  (2) a LOGARITHMIC stamp bonus (bounded; prevents the +6000x compound-economy runaway).
        # Total is cumulative across runs so meta-progression always moves forward.
        import math as _m
        prestige_floor = (1 + FIRST_PRESTIGE_BUFF) ** state["prestige_count"]
        stamp_bonus = _m.log10(state["stamps"] + 1) * STAMP_BUFF
        base_buff = prestige_floor * (1 + stamp_bonus)
        # territory kept but dormant -> sun production re-ramps from DORMANT_RATE
        kept_sun = state["sun"] * DORMANT_RATE
        # reset economy
        state["cc"] = 0; state["lifetime_cc"] = 0; state["red_pill"] = 0; state["visas"] = 0
        state["gen_counts"] = {}; state["fleet_cap"] = 0; state["owned_ships"] = []
        state["upg_prod_lvl"] = 0; state["active_wars"] = []; state["pending_research"] = None
        state["researched"] = set(["Shuttle"])
        state["ship_counts"] = {}
        # Admirals come from PERMANENTLY captured capitals -> they survive prestige (territory is kept).
        # Fleet is reset, but the defected commanders remain loyal across Abdications.
        state["admirals"] = int(A.get("Starting admirals", 1)) + state.get("perm_admirals", 0)
        state["sun"] = kept_sun
        state["prestige_mult"] = base_buff
        # PERMANENT perk: each prestige raises reachable tier by 1 (survives the reset).
        # prestige 1 -> +1 (cap reaches tier 4), prestige 2 -> +2 (tier 5 / Fringe).
        state["perm_range_bonus"] = min(state["prestige_count"], 2)
        state["fleet_range"] = fleet_max_range()
        milestones.setdefault(f"prestige_{state['prestige_count']}", t)

    def step(seconds, online):
        eff = 1.0 if online else offline_eff
        # advance the compound chain first (higher tiers grow lower tiers)
        advance_chain(seconds * eff)
        rate = cc_per_sec()
        gain = rate * seconds * eff
        if online and sum(state["gen_counts"].values()) < 3:
            gain += seconds * 5 * click_yield   # realistic early mash
        state["cc"] += gain
        state["lifetime_cc"] += gain
        # Red Pill: the CC->RP primer is a BOOTSTRAP only. Under a compound economy, an
        # uncapped primer (rate * RP_PRIMER) becomes a firehose that dwarfs region income and
        # removes war's resource cost. Hard-cap it so it can fund ~the first conquest, then
        # conquered-region drops become the real (and only meaningfully scaling) war engine.
        primer = min(rate * RP_PRIMER, RP_PRIMER_CAP)
        state["red_pill"] += (primer + region_red_pill_per_sec()) * seconds * eff

    def step_long(total_seconds, online, substep=3600):
        # sub-step long durations so compounding accrues correctly over offline gaps
        remaining = total_seconds
        while remaining > 0:
            chunk = min(substep, remaining)
            step(chunk, online)
            remaining -= chunk

    # run
    for active_s, offline_s in schedule:
        if offline_s > 0:
            capped = min(offline_s, offline_cap_s)
            step_long(capped, online=False)
            t += offline_s
            resolve_war(); resolve_research()
        elapsed = 0
        while elapsed < active_s:
            chunk = 10
            step(chunk, online=True)
            t += chunk
            try_buy_generators(); try_buy_upgrade()
            try_research(); resolve_research()
            convert_cc_to_visas(); try_build_ship()
            try_start_war(); resolve_war()
            elapsed += chunk
        # WALL CHECK: a genuine stall = can't progress, no war pending, and it's persisted.
        # Either territory-gated research OR can't afford the breakthrough ship.
        stalled = (not can_progress()) and len(state["active_wars"]) == 0 and len(conquered) > 0
        if stalled:
            state["stall_sessions"] = state.get("stall_sessions", 0) + 1
        else:
            state["stall_sessions"] = 0
        # if stalled ~3 sessions (under a day) and economy is mature, prestige is the way through.
        # A real player abdicates almost immediately on seeing no reachable target; 3 sessions
        # confirms it's a genuine range-wall, not a transient between-wars gap.
        progressed = len(conquered) > state.get("conquered_at_last_prestige", -1)
        if (state["stall_sessions"] >= 4 and state["lifetime_cc"] > war_unlock_lifetime * 5
                and (state["prestige_count"] == 0 or progressed)):
            milestones.setdefault("hit_wall", t)
            do_prestige()
            state["conquered_at_last_prestige"] = len(conquered)
            state["stall_sessions"] = 0

        if "first_automation" not in milestones and sum(state["gen_counts"].values()) >= 1:
            milestones["first_automation"] = t
        if "war_unlocked" not in milestones and state["lifetime_cc"] >= war_unlock_lifetime:
            milestones["war_unlocked"] = t
        if "first_ship" not in milestones and sum(state["ship_counts"].values())>0:
            milestones["first_ship"] = t
        primer_rp = min(cc_per_sec() * RP_PRIMER, RP_PRIMER_CAP)
        region_rp = region_red_pill_per_sec()
        if "war_self_funding" not in milestones and region_rp > primer_rp and region_rp > 0:
            milestones["war_self_funding"] = t
        log.append({
            "day": round(t/86400,2), "t_hours": round(t/3600,1),
            "cc": state["cc"], "lifetime_cc": state["lifetime_cc"], "cc_per_sec": round(cc_per_sec(),2),
            "generators": sum(state["gen_counts"].values()), "upg_lvl": state["upg_prod_lvl"],
            "red_pill": round(state["red_pill"],1), "rp_primer/s": round(primer_rp,2),
            "rp_region/s": round(region_rp,2), "visas": round(state["visas"],1),
            "ships": sum(state["ship_counts"].values()), "fleet_cap": state["fleet_cap"],
            "researched": len(state["researched"]), "conquered": len(conquered),
            "deepest_tier": deepest_tier_conquered(), "fleet_range": state["fleet_range"],
            "prestige": state["prestige_count"], "prestige_mult": round(state["prestige_mult"],2),
            "admirals": state["admirals"], "active_wars": len(state["active_wars"]),
            "sun": round(state["sun"],1),
        })

    return A, log, milestones, conquered, galaxy

def fmt(n):
    if n >= 1e9: return f"{n/1e9:.2f}B"
    if n >= 1e6: return f"{n/1e6:.2f}M"
    if n >= 1e3: return f"{n/1e3:.1f}k"
    return f"{n:.0f}"

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    A, log, ms, conquered, galaxy = simulate(days=days)

    # write CSV
    with open("playthrough_log.csv","w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(log[0].keys()))
        w.writeheader()
        for row in log: w.writerow(row)

    print(f"=== PLAYTHROUGH SIM — {days} days, {len(log)} sessions ===\n")
    print("MILESTONES (game-time when reached):")
    def hrs(s): 
        return f"{s/3600:.1f}h (day {s/86400:.1f})"
    order = ["first_automation","war_unlocked","first_ship","conquer_1","war_self_funding",
             "conquer_5","conquer_10","hit_wall","prestige_1","admiral_1","conquer_25","prestige_2",
             "admiral_2","conquer_40","admiral_3","conquer_50"]
    for k in order:
        if k in ms:
            print(f"  {k:<18} {hrs(ms[k])}")
    print(f"\n  Total conquered: {len(conquered)} / {len(galaxy)} regions")

    print("\nPROGRESSION SNAPSHOTS:")
    print(f"  {'day':>5} {'CC/s':>10} {'gens':>6} {'rsch':>5} {'ships':>6} {'cap':>5} {'conq':>5} {'tier':>5} {'adm':>4} {'prs':>4} {'mult':>6}")
    seen=set()
    for row in log:
        d=int(row['day'])
        if d not in seen:
            seen.add(d)
            print(f"  {row['day']:>5} {row['cc_per_sec']:>10,.0f} {int(row['generators']):>6} {row['researched']:>5} {row['ships']:>6} {row['fleet_cap']:>5} {row['conquered']:>5} {row['deepest_tier']:>5} {row['admirals']:>4} {row['prestige']:>4} {row['prestige_mult']:>6.2f}")

    print("\nRED PILL ECONOMY (primer vs region income):")
    print(f"  {'day':>5} {'banked':>10} {'primer/s':>9} {'region/s':>9} {'source':>10}")
    seen=set()
    for row in log:
        d=int(row['day'])
        if d not in seen:
            seen.add(d)
            src = "REGION" if row['rp_region/s'] > row['rp_primer/s'] else "primer"
            print(f"  {row['day']:>5} {fmt(row['red_pill']):>10} {row['rp_primer/s']:>9.2f} {row['rp_region/s']:>9.2f} {src:>10}")

    # ---- automatic health flags ----
    print("\nHEALTH FLAGS:")
    flags=[]
    if "first_automation" not in ms or ms["first_automation"] > 300:
        flags.append("First automation took >5min — early hook may be too slow.")
    if "war_unlocked" not in ms:
        flags.append("War never unlocked in this window — CC ramp too slow OR unlock threshold too high.")
    if "first_ship" not in ms:
        flags.append("Player never afforded a ship — Visa cost may be too brutal for this timeframe.")
    elif "war_unlocked" in ms and ms["first_ship"] - ms["war_unlocked"] > 3*86400:
        flags.append("Gap from war-unlock to first ship >3 days — Visa grind may sap momentum.")
    if len(conquered)==0:
        flags.append("Zero conquests — war loop not reachable in this window.")
    if len(conquered)>=len(galaxy):
        flags.append("FULL galaxy conquered — too fast; increase tier cost scale or Visa costs.")
    final = log[-1]
    if final["cc_per_sec"] > 0 and final["generators"]>0:
        # crude runaway check: did CC/s 100x in last 3 days?
        pass
    if not flags:
        flags.append("No critical pacing flags in this window. Inspect snapshots for feel.")
    for fl in flags:
        print(f"  ⚠ {fl}")
    print("\nWrote playthrough_log.csv")
