"""Research for dispersed cities, external supply networks, and safer treatment."""
import struct

from last_autumn import AUTUMN_TABS
from steel_logistics import two_scout_teams


EDGE_GAMEPLAY = {"StormDutyClothing", "RedeploymentKits", "ConservativeSurgery"}
OUTPOST_TECH = "OutpostNetworkCharters"


def global_change(offset, value):
    def transform(payload):
        # This native global modifier is neutral apart from its automaton bonus.
        assert len(payload) == 186 and payload[:12] == struct.pack("<IfI", 0, -1, 2)
        assert struct.unpack_from("<f", payload, 150)[0] == struct.unpack("<f", struct.pack("<f", 0.1))[0]
        assert offset in (65, 69, 166) and payload[offset:offset + 4] == struct.pack("<f", 1)
        revised = bytearray(payload)
        struct.pack_into("<f", revised, 150, 0)
        struct.pack_into("<f", revised, offset, value)
        return bytes(revised)

    return transform


def add_gameplay_upgrades(add, floats, places, tabs):
    global_source = "E 4_Automaton Efficiency"
    medical = "F 2_MedPost Upgrade"
    medical_target = (places["Medical Post"].hex(), "30aa2c27e02dce83494392ae5c1f2261")
    surgery = ("Medical Posts reduce the amputation risk of Radical Treatment by 75%. "
               "This gives Radical Treatment a safer long-term role in cities with few Infirmaries. "
               "The Radical Treatment law must be active for this effect to matter.")
    clothing = ("Citizens have a 50% lower chance of illness caused by low temperatures. "
                "This helps sustain outdoor and dispersed workplaces during cold weather.")
    redeployment = ("Building construction takes 75% less time. Construction crews finish new sites "
                    "four times as quickly, making it easier to relocate production as deposits run out or the weather changes.")
    heating = ("All heat zones gain 50% more radius, including the Generator, Steam Hubs, and Braziers "
               "where present. Wider coverage allows districts to spread farther from each heat source.")

    add("ConservativeSurgery", "Conservative Surgical Protocols", surgery,
        1, 10, 32, 12, 6, medical, [(medical, "Medical Post Upgrade")],
        place_effect=medical_target, transform=floats((0.5, 0.25)), icon=(4, 9), tab=tabs["food"])
    add("StormDutyClothing", "Storm Duty Clothing", clothing,
        2, 14, 55, 30, 10, global_source, [], transform=global_change(166, 0.5), icon=(5, 9), tab=tabs["exploration"])
    add("RedeploymentKits", "Prefab Assembly Teams", redeployment,
        1, 8, 32, 14, 7, global_source, [], transform=global_change(65, 0.25), icon=(3, 6), tab=tabs["exploration"])
    add("SteamTrunklines", "District Steam Trunklines", heating,
        3, 12, 80, 50, 12, global_source, [("H 1_SteamHub", "Steam Hub")],
        transform=global_change(69, 1.5), icon=(1, 6), tab=tabs["heating"])
    add("EdgeBrazierNetworks", "Brazier District Networks", heating,
        3, 8, 70, 40, 11, global_source, [("[Reconquest] HC 1_Brazier", "Braziers")],
        transform=global_change(69, 1.5), icon=(10, 3), tab=tabs["heating"])
    add(OUTPOST_TECH, "Outpost Network Charters",
        "Each Outpost Depot can dispatch two additional Outpost teams, supporting up to three Outposts per depot. This enables a city that imports more of its basic supplies.",
        3, 16, 70, 45, 12, "E 2_ScoutsLimit", [("E 3_ExpeditionCenter", "Outpost Depot")],
        target_names=["Expedition Center", "[Winterhome] Expedition Center"], transform=two_scout_teams,
        icon=(0, 10), tab=tabs["exploration"])

    autumn = AUTUMN_TABS
    add("AutumnConservativeSurgery", "Conservative Surgical Protocols", surgery,
        2, 2, 32, 12, 6, "[Builders] FM 1_MedPost Upgrade",
        [("[Builders] FM 1_MedPost Upgrade", "Medical Post Upgrade")],
        place_effect=medical_target, transform=floats((0.5, 0.25)), icon=(4, 9), tab=autumn["food"])
    add("AutumnStormDutyClothing", "Storm Duty Clothing", clothing,
        2, 12, 45, 25, 9, global_source, [], transform=global_change(166, 0.5), icon=(5, 9), tab=autumn["heat"])
    add("AutumnRedeploymentKits", "Prefab Assembly Teams", redeployment,
        1, 20, 32, 14, 7, global_source, [], transform=global_change(65, 0.25), icon=(3, 6), tab=autumn["construction"])
    add("AutumnSteamTrunklines", "Brazier District Networks", heating,
        3, 2, 70, 40, 11, global_source, [("[Builders] HC 2_Brazier", "Braziers")],
        transform=global_change(69, 1.5), icon=(10, 3), tab=autumn["heat"])
    add("AutumnForagerWeb", "Forager Supply Web",
        "Allows two additional Foragers' Quarters and forager teams, expanding the food supply that can be gathered outside the city.",
        3, 4, 65, 35, 10, "[Builders] FF 1_Foragers_+1", ["AutumnExtraForagers"],
        transform=two_scout_teams, icon=(2, 10), tab=autumn["food"])
