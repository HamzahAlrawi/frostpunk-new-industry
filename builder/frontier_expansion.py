"""Second arcs for cities that have completed their founding campaign."""

FRONT_DAYS = (5, 10, 16, 23)
FRONT_HEAT = (1, 2, 2, 3)
DOCTRINES = (
    ("civic", "Civic Commonwealth", "Homes and civic buildings gain +1 insulation; healthcare gains 60% efficiency. Industry loses 10% efficiency. No upkeep.", {}),
    ("league", "Industrial League", "Factories and Steelworks gain 65% efficiency; Workshops gain 30%. Upkeep: 80 coal and 5 steel every six hours.", {"Coal": 80, "Steel": 5}),
    ("grid", "Emergency Heat Grid", "Every insulated building gains +2 insulation. Upkeep: 125 coal every six hours.", {"Coal": 125}),
    ("shelter", "Shelter Network", "Homes, healthcare and civic buildings gain +2 insulation. Workshop efficiency falls by 15%. No upkeep.", {}),
    ("closed", "Closed-loop Industry", "Industrial and extraction automatons gain 90% efficiency; humans lose 20%. Upkeep: one steam core every two days.", {"Steam Cores": 1}),
    ("partnership", "Human-machine Partnership", "Industrial and extraction workers gain 30% efficiency; automatons gain 40%. Medical efficiency falls by 10%. No upkeep.", {}),
)


def extend(stories, build, tech, produce, automate):
    additions = (
        [
            dict(phase=7, title="Open the public works", goals=[build("Build four Large Resource Depots", ["Resource Depot Big"], 4),
                 tech("Research Modular Warehousing", "mod:ModularWarehouses"), build("Build three Steam Hubs", ["Steam Hub"], 3)]),
            dict(phase=8, title="Give the capital a second supply chain", goals=[build("Build two Wall Drills", ["WallDrill", "WallDrillSteam", "WallDrillAdvanced"], 2),
                 tech("Research Industrial Tool Libraries", "mod:ToolLibraries"), build("Build two Infirmaries", ["Ambulatorium"], 2)]),
            dict(phase=9, title="Keep the regional works open", checks=8, reserves={"Coal": 3000, "Wood": 800, "Steel": 600},
                 payment={"Wood": 50, "Steel": 35}, goals=[], reward="works"),
        ],
        [
            dict(phase=7, title="Build a reserve heat grid", goals=[tech("Research Steam Trunk Lines", "mod:SteamTrunklines"),
                 build("Build four Steam Hubs", ["Steam Hub"], 4), build("Build four Large Resource Depots", ["Resource Depot Big"], 4)]),
            dict(phase=8, title="Bring the wards off the emergency rota", goals=[tech("Research Protected Healthcare Heaters", "mod:ProtectedHealthcareHeaters"),
                 build("Build three Infirmaries", ["Ambulatorium"], 3), tech("Research Deep Coal Bins", "mod:DeepCoalBins")]),
            dict(phase=9, title="Run the grid under stress", checks=12, reserves={"Coal": 4500, "Food Rations": 900},
                 payment={"Coal": 120, "Food Rations": 25}, goals=[], reward="reservegrid"),
        ],
        [
            dict(phase=7, title="Build an independent parts line", goals=[tech("Research Core Fabrication Cells", "mod:MassCoreFabrication"),
                 build("Build three Factories", ["Factory"], 3), produce(4)]),
            dict(phase=8, title="Retool the machine workforce", goals=[automate(0.60), produce(4),
                 tech("Research Steelworks Continuous Casting", "mod:SteelworksContinuousCasting")]),
            dict(phase=9, title="Keep the machine network supplied", checks=8,
                 reserves={"Coal": 4000, "Steel": 900, "Steam Cores": 6}, payment={"Coal": 80, "Steel": 30},
                 goals=[automate(0.60)], reward="machineworks"),
        ],
    )
    reserves = (
        {"Coal": 3200, "Wood": 650, "Steel": 500, "Food Rations": 800, "Steam Cores": 3},
        {"Coal": 4200, "Wood": 450, "Steel": 350, "Food Rations": 850},
        {"Coal": 4200, "Steel": 700, "Food Rations": 900, "Steam Cores": 5},
    )
    for index, (story, missions) in enumerate(zip(stories, additions)):
        for branch, (key, title, description, upkeep) in zip(story["branches"], DOCTRINES[2*index:2*index+2]):
            assert branch["bonus"] == key
            branch.update(title=title, description=description)
            if upkeep:
                branch.update(upkeep=upkeep, period=2 if key == "closed" else 0.25)
        story["missions"][-1].update(checks=(8, 12, 8)[index], reserves=reserves[index])
        story["missions"].extend(missions)
    stories[1]["description"] = (
        "Four thermal fronts arrive after 5, 10, 16 and 23 days. "
        "Build redundant heating and healthcare, choose how to protect the city, and keep the Generator and storm reserves running."
    )
    return stories
