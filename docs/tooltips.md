# Building modifier tooltips

Version 3.14.0 fills the display name and description of every mod-added modifier:
326 records covering research, law benefits, human and automaton efficiency,
heating, storage and other sources. All 13 supported language tables receive the
mod's English text, as with the other New Industry additions.

Research descriptions and building modifier sources are separate game fields.
Both are now populated. Building source descriptions identify the research or law
responsible for the benefit. The game supplies the numeric value beside it.

## Cumulative insulation sources

The following chains use one active heat source per affected building. Further
research increases its contribution instead of adding another heat-tooltip row.
The research nodes, prices, prerequisites and extra benefits are retained.

| Building source | Added insulation as its stages are researched |
| --- | --- |
| Citywide Thermal Envelope | +1, +2, +3, +4, +5, +7 |
| Healthcare Insulation | +1, then +3 from the two added late healthcare insulation stages |
| Hothouse Insulation | +1, then +3 from Hothouse Insulation III / Winter Conservatories |
| Cookhouse Insulation | +1, then +3 from Steam Shells / Steam-Jacketed Kitchens |
| Housing Insulation | Houses: +1, then +2; Bunkhouses: +1 when District Underfloor Heating is researched |
| Army Warehouse Insulation | +1, then +2 from Draught Baffles / Enclosed Warehouse Winches |

These are the contributions of the listed mod research chains. Native insulation,
other research and signed laws retain their own source labels. Thermal Envelope's
illness and heat-zone-radius benefits still apply at their original stages.
Efficiency bonuses on mixed upgrades such as Winter Conservatories and Enclosed
Warehouse Winches retain their values.

The build checks actual serialized source fields in every language and compares
heat totals and visible source counts at every reachable stage in all applicable
scenarios. All native modifier records are preserved. Research, law and modifier
identifiers are retained; no saves are rewritten. Live tooltip UI validation has
not been performed for this beta.
