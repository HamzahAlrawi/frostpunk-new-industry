"""Pack added research into themed tabs with scenario-aware geometric checks.

Positions use native research-grid units. Seven lanes leave a three-column gap
between icons. Requirements in another tab remain real requirements and are
listed by name in the tooltip, but do not draw a line across this tab.
"""
from collections import Counter
import itertools


TAB_NAMES = ("Engineering", "Industry", "City Life", "Logistics")
LANES = (2, 5, 8, 11, 14, 17, 20)


def preferred_tab(key):
    overrides = {
        'MedicalHeat3':2,'MedicalHeat4':2,'HothouseHeat3':1,'HothouseHeat4':1,
        'CookhouseHeat2':2,'CoalMineHeat':1,'DrillHeat':1,'IndustrialStorm':1,
        'ToolLibraries':0,'CoalCircuit':3,'SawmillSurvey':3,'MasteryIrrigation':0,
        'CitywideLagging':3,'CitywideLagging2':3,'CitywideLagging3':3,
        'HuntingSleds':3,
        'SeedSelection2':3,
        'SawmillWindwalls':1,'EdgeWarehouseBaffles':0,'EdgeTimberMaps':3,
        'GatheringHeat3':1,'WorkshopSteam':0,'WorkshopBench':0,
        'StormDutyClothing':2,'MiningCoreMounts':1,'ScrapRecovery':3,
        'StackedDepots':1,'RetortCharcoal':1,'MineAirlocks':0,'MasteryIrrigation':2,
    }
    if key in overrides:
        return overrides[key]
    if any(s in key for s in ("Depot", "Storage", "Bins", "Cells", "Stockyard", "Warehous", "CargoRacks",
                              "Scout", "Convoy", "Outpost", "Forager", "Dock", "Reloading", "Crane", "Cargo", "Redeploy")):
        # The Army Warehouse is a production building, not storage.
        return 1 if key.startswith("EdgeWarehouse") else 3
    if any(s in key for s in ("Workshop", "Generator", "Governor", "Hub", "Overdrive", "Automaton", "Clockwork",
                              "Citywide", "Trunklines", "Brazier", "StormDuty", "Heat", "Lining", "Liners", "Lagging",
                              "Workwear", "Windwall", "Winterization", "Worksite", "FabricationSafety", "Guard")):
        return 0
    if any(s in key for s in ("Gathering", "Sawmill", "Timber", "Steel", "Thumper", "Coal", "Drill", "Mine",
                              "Kiln", "Cores", "Factory", "Scrap", "ToolLibraries", "WorksNetwork", "Profile", "Exchanger", "Composite", "Fabrication")):
        return 1
    return 2


def orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segment_conflict(a, b, c, d):
    p, q, r, s = orientation(a, b, c), orientation(a, b, d), orientation(c, d, a), orientation(c, d, b)
    if p * q < 0 and r * s < 0:
        return True
    if p == q == r == s == 0:
        axis = 0 if a[0] != b[0] else 1
        overlap = min(max(a[axis], b[axis]), max(c[axis], d[axis])) - max(min(a[axis], b[axis]), min(c[axis], d[axis]))
        return overlap > 0
    return False


def point_hit(a, b, p):
    dx, dy = b[0] - a[0], b[1] - a[1]
    mx, my = p[0] - a[0], p[1] - a[1]
    length = dx * dx + dy * dy
    dot = mx * dx + my * dy
    return 0 < dot < length and (mx * dy - my * dx) ** 2 < 1.05 ** 2 * length


def geometry_errors(techs):
    """One scenario and one tab, including only active, displayed nodes."""
    by_guid = {t["guid"]: t for t in techs}
    point = {g: (t["column"], t["tier"] * 2) for g, t in by_guid.items()}
    edges = [(p, t["guid"]) for t in techs for p in t["requires"] if p in by_guid]
    errors = []
    for a, b in itertools.combinations(techs, 2):
        if a["tier"] == b["tier"] and abs(a["column"] - b["column"]) < 3:
            errors.append(("icons", a["id"], b["id"]))
    for a, b in edges:
        for g, t in by_guid.items():
            if g not in (a, b) and point_hit(point[a], point[b], point[g]):
                errors.append(("line through icon", by_guid[a]["id"], by_guid[b]["id"], t["id"]))
    for (a, b), (c, d) in itertools.combinations(edges, 2):
        if segment_conflict(point[a], point[b], point[c], point[d]):
            errors.append(("lines", *(by_guid[g]["id"] for g in (a, b, c, d))))
    return errors


def _solve(nodes, masks):
    by = {t["guid"]: t for t in nodes}
    edges = [(p, t["guid"]) for t in nodes for p in t["requires"] if p in by]
    degree = Counter(g for pair in edges for g in pair)
    neighbors = {g: {b if a == g else a for a, b in edges if g in (a, b)} for g in by}
    placed = {}
    steps = 0

    def position(g):
        return placed[g], by[g]["tier"] * 2

    def valid(g, column):
        mask = masks[g]
        y = by[g]["tier"]
        if any(masks[h] & mask and by[h]["tier"] == y and abs(column - x) < 3 for h, x in placed.items()):
            return False
        placed[g] = column
        active_edges = [(a, b) for a, b in edges if a in placed and b in placed]
        for a, b in active_edges:
            common = masks[a] & masks[b]
            for h in placed:
                if h not in (a, b) and masks[h] & common and (g in (a, b, h)) and point_hit(position(a), position(b), position(h)):
                    del placed[g]
                    return False
        for i, (a, b) in enumerate(active_edges):
            for c, d in active_edges[i + 1:]:
                if g in (a, b, c, d) and masks[a] & masks[b] & masks[c] & masks[d]:
                    if segment_conflict(position(a), position(b), position(c), position(d)):
                        del placed[g]
                        return False
        del placed[g]
        return True

    def search():
        nonlocal steps
        steps += 1
        if steps > 1500:
            return False
        if len(placed) == len(nodes):
            return True
        remaining = [g for g in by if g not in placed]
        # Fill constrained rows first, then align parent/child branches.
        candidates = {}
        for g in remaining:
            candidates[g] = [x for x in LANES if valid(g, x)]
            if not candidates[g]:
                return False
        # A long vertical prerequisite can leave six lanes for seven nodes in
        # the intervening tier. Individual domains are nonempty in that case,
        # but the row cannot fit. Reject it before exploring permutations of
        # unrelated branches; diagonal paths through lane gaps remain possible.
        for bit in range(max(masks.values(),default=0).bit_length()):
            for tier in {by[h]['tier'] for h in remaining}:
                row=[h for h in remaining if by[h]['tier']==tier and masks[h] & (1<<bit)]
                if row and len(set().union(*(set(candidates[h]) for h in row)))<len(row):
                    return False
        g = min(remaining, key=lambda h: (0 if degree[h] else 1, len(candidates[h]), -sum(n in placed for n in neighbors[h]), -degree[h], by[h]["id"]))
        nearby = [placed[n] for n in neighbors[g] if n in placed]
        order = sorted(candidates[g], key=lambda x: (sum(abs(x - n) for n in nearby), x))
        for x in order:
            placed[g] = x
            if search():
                return True
            del placed[g]
        return False

    return placed if search() else None


def arrange(specs, scenario_additions, guid):
    # Reuse the previous City Mastery GUID for Engineering; keep save identifiers.
    categories = [guid("city-mastery-category").hex()] + [guid("research-tab/" + name).hex() for name in TAB_NAMES[1:]]
    active = {g for ids in scenario_additions.values() for g in ids}
    nodes = [t for t in specs if t["guid"] in active]
    masks = {t["guid"]: sum(1 << i for i, ids in enumerate(scenario_additions.values()) if t["guid"] in ids) for t in nodes}
    assigned = {t["guid"]: t.get('preferred_tab',preferred_tab(t["id"])) for t in nodes}

    def capacity_ok(assignment):
        for ids in scenario_additions.values():
            counts = Counter((assignment[g], t["tier"]) for t in nodes if (g := t["guid"]) in ids)
            if max(counts.values(), default=0) > len(LANES):
                return False
        return True

    # Balance oversubscribed theme rows. Sharing a slot between mutually exclusive
    # scenario variants is safe; counts are evaluated per scenario, not their union.
    for _ in range(100):
        crowded = []
        for ids in scenario_additions.values():
            count = Counter((assigned[t["guid"]], t["tier"]) for t in nodes if t["guid"] in ids)
            crowded += [(cat, tier, ids) for (cat, tier), n in count.items() if n > len(LANES)]
        if not crowded:
            break
        cat, tier, ids = crowded[0]
        options = [t for t in nodes if t["guid"] in ids and assigned[t["guid"]] == cat and t["tier"] == tier
                   and 'Workshop' not in t['id']]
        moved = False
        for tech in sorted(options, key=lambda t: t["id"], reverse=True):
            g = tech["guid"]
            for destination in range(4):
                if destination == cat:
                    continue
                if all(sum(assigned[t["guid"]] == destination and t["tier"] == tier for t in nodes if t["guid"] in members) < len(LANES)
                       for members in scenario_additions.values() if g in members):
                    assigned[g] = destination
                    moved = True
                    break
            if moved:
                break
        assert moved, (cat, tier)
    assert capacity_ok(assigned)

    for cat in range(4):
        group = [t for t in nodes if assigned[t["guid"]] == cat]
        # Last Autumn never coexists with the cold-city research lists.
        # Solve the independent layouts separately instead of multiplying the
        # search space by permutations of mutually exclusive nodes.
        cold = [t for t in group if t.get('scenario_scope') != 'autumn']
        autumn = [t for t in group if t.get('scenario_scope') == 'autumn']
        positions = {}
        for subgroup in (cold, autumn):
            print('Laying out',TAB_NAMES[cat],len(subgroup),'nodes',flush=True)
            result = _solve(subgroup, masks)
            assert result is not None, ("No collision-free layout", TAB_NAMES[cat],
                [(t['id'],t['tier']) for t in subgroup])
            positions.update(result)
        for tech in group:
            tech["category"] = categories[cat]
            tech["column"] = positions[tech["guid"]]
            tech["tab"] = TAB_NAMES[cat]
    for ids in scenario_additions.values():
        for category in categories:
            errors = geometry_errors([t for t in nodes if t["guid"] in ids and t["category"] == category])
            assert not errors, errors
    return list(zip(TAB_NAMES, categories))
