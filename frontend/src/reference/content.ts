// What the /reference page says about the data, the documents and the judgement values behind the
// routes. The numbers themselves come from the API, so they cannot drift from the engine; the text
// here must be kept in step with README.md (Data sources), NOTICE and docs/parameters.md.

export interface Dataset {
  name: string;
  publisher: string;
  use: string;
  licence: string;
  url?: string;
  licenceUrl?: string;
}

export interface Work {
  citation: string;
  use: string;
  url?: string;
}

/** How a value was reached, as in docs/parameters.md. "Chosen" values are judgements. */
export type Basis = "Cited" | "Derived" | "Chosen";

export interface Basised {
  basis: Basis;
  note: string;
}

const CC_BY_4 = "https://creativecommons.org/licenses/by/4.0/";

export const DATASETS: Dataset[] = [
  {
    name: "Walking network, buildings and entrances",
    publisher: "© OpenStreetMap contributors, through the Overpass API and OSMnx",
    use: "The paths routes follow, steps, the buildings used as start, destination and shelter, and their entrances.",
    licence: "ODbL 1.0",
    url: "https://www.openstreetmap.org/copyright",
    licenceUrl: "https://opendatacommons.org/licenses/odbl/1-0/",
  },
  {
    name: "Small Areas for Census of Land Use and Employment (CLUE)",
    publisher: "City of Melbourne",
    use: "The Southbank boundary, the area the system covers.",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/small-areas-for-census-of-land-use-and-employment-clue/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Stormwater Pits",
    publisher: "City of Melbourne",
    use: "Drain inlets that open to the surface, where a high tide backs up through the drains.",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/stormwater-pits/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Footpath steepness",
    publisher: "City of Melbourne",
    use: "The gradient of each council footpath section: every route shows its steepest and gentlest measured gradient, and wheelchair and scooter routes leave out paths steeper than 1:14.",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/footpath-steepness/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Pedestrian Network",
    publisher: "City of Melbourne",
    use: "An alternative walking network, used to check the OpenStreetMap one.",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/pedestrian-network/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Digital Elevation Model (DEM) of Australia derived from LiDAR 5 Metre Grid",
    publisher: "© Commonwealth of Australia (Geoscience Australia), through its 2025 web service",
    use: "Ground height, from which the depth of water at every point is worked out.",
    licence: "CC BY 4.0",
    url: "https://doi.org/10.26186/89644",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Vicmap Planning, Planning Scheme Overlay Polygon (LSIO, SBO, FO)",
    publisher: "© State of Victoria (Department of Transport and Planning)",
    use: "Land expected to flood in a 1-in-100-year event; shown for context in the Streamlit app, not used for routing.",
    licence: "CC BY 4.0",
    url: "https://discover.data.vic.gov.au/dataset/vicmap-planning-planning-scheme-overlay-polygon",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Place search",
    publisher: "OpenStreetMap Nominatim",
    use: "Finding a place typed into the search boxes.",
    licence: "ODbL 1.0; usage policy applies",
    url: "https://operations.osmfoundation.org/policies/nominatim/",
    licenceUrl: "https://opendatacommons.org/licenses/odbl/1-0/",
  },
  {
    name: "Basemap",
    publisher: "OpenFreeMap (Positron style), OpenMapTiles schema, © OpenStreetMap contributors",
    use: "The map drawn under the routes; OpenStreetMap's own tiles if it does not load.",
    licence: "ODbL 1.0 data; OpenMapTiles design CC BY 4.0",
    url: "https://openfreemap.org/",
    licenceUrl: "https://github.com/openmaptiles/openmaptiles/blob/master/LICENSE.md",
  },
];

export const FLOOD_DOCUMENTS: Work[] = [
  {
    citation: "Melbourne Water (2026). Southbank Precinct Local Floodplain Development Plan 2026.",
    url: "https://www.melbournewater.com.au/services/projects/southbank-precinct-flood-risk-and-development-planning",
    use: "How Southbank floods (storm tide and river flows, local stormwater, drains that cannot discharge at high tide); 500 mm as safe pedestrian access, 300 mm for vulnerable uses.",
  },
  {
    citation: "GHD (2017). Melbourne Water – Fishermans Bend: Baseline drainage plan options. Report 31/34157, prepared for Melbourne Water.",
    url: "https://www.vic.gov.au/sites/default/files/2024-11/GHD-Baseline-Drainage-Plan-Report.pdf",
    use: "Storm tide levels for Port Phillip Bay (Table 1): 1-in-20-year 1.25 m, 1-in-100-year 1.60 m, 1-in-100-year in 2100 2.40 m AHD.",
  },
  {
    citation:
      "Water Technology (2023). Erosion Hazard Summary Report – Port Phillip Bay Coastal Erosion Hazards. Report to the Department of Energy, Environment and Climate Action, part of the Port Phillip Bay Coastal Hazard Assessment.",
    url: "https://www.marineandcoasts.vic.gov.au/coastal-programs/port-phillip-bay-coastal-hazard-assessment",
    use: "Highest astronomical tide at Williamstown, 0.59 m AHD (Table 2-1): the light flooding level.",
  },
  {
    citation: "City of Melbourne Municipal Emergency Management Planning Committee and VICSES (2025). City of Melbourne Flood and Storm Sub-Plan, version 1.0.",
    url: "https://www.ses.vic.gov.au/documents/d/www/city-of-melbourne-memp-flood-and-storm-sub-plan",
    use: "A high tide reduces the drains' capacity and backflow surcharges around the pits.",
  },
  {
    citation: "VICSES (2021). Southbank Local Flood Guide.",
    url: "https://www.ses.vic.gov.au/plan-and-stay-safe/flood-guides/melbourne-city-council",
    use: "Streets expected to flood at the Southbank gauge, used to check the scenarios; the gauge's major flood level.",
  },
  {
    citation: "Victoria Planning Provisions, clause 13.01-2S Coastal inundation and erosion.",
    url: "https://planning-schemes.app.planning.vic.gov.au/Victoria%20Planning%20Provisions/ordinance/13.01-2S",
    use: "Planning for 0.8 m of sea level rise by 2100: the extreme flooding level.",
  },
];

export const PEOPLE_DOCUMENTS: Work[] = [
  {
    citation:
      "Drillis, R. & Contini, R. (1966). Body segment parameters. Technical Report 1166-03, School of Engineering and Science, New York University.",
    use: "Ankle, knee and hip heights as fractions of a person's height.",
  },
  {
    citation:
      "Feng, Y., Brenner, C. & Sester, M. (2020). Flood severity mapping from Volunteered Geographic Information by interpreting water level from images containing people: A case study of Hurricane Harvey. ISPRS Journal of Photogrammetry and Remote Sensing, 169, 301–319.",
    use: "Ankle, knee and hip as the waterlines that grade how severe a flood is: the boundaries of the four flood levels.",
    url: "https://doi.org/10.1016/j.isprsjprs.2020.09.011",
  },
  {
    citation: "Smith, G. P., Davey, E. K. & Cox, R. J. (2014). Flood Hazard. WRL Technical Report 2014/07, Water Research Laboratory, UNSW.",
    url: "https://www.unsw.edu.au/content/dam/pdfs/engineering/civil-environmental/water-research-laboratory/publications/WRL-TR2014-07-Flood-hazard.pdf",
    use: "0.5 m as the depth limit for people (H2) and children's wading limit; vulnerable people should avoid flowing floodwater.",
  },
  {
    citation: "Australian Bureau of Statistics (2012). Australian Health Survey: First Results, 2011–12 (cat. no. 4364.0.55.001).",
    url: "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/4364.0.55.0012011-12",
    use: "Average adult height, 1.69 m: the 1.70 m reference adult used to describe the flood levels.",
  },
  {
    citation: "Standards Australia (2021). AS 1428.1:2021 Design for access and mobility, Part 1: General requirements for access – New building work.",
    url: "https://store.standards.org.au/product/as-1428-1-2021",
    use: "An accessible path of travel has no steps and no ramp steeper than 1:14 (kerb ramps up to 1:8 over 1.52 m), so wheelchair and scooter routes use neither.",
  },
];

export const MOBILITY_DOCUMENTS: Work[] = [
  {
    citation: "Minniemobil (2015). MM-01 / MM-02 mobility scooter owner's manual.",
    url: "https://minniemobil.com/wp-content/uploads/2015/07/minniemobil-mm-01-mm-02-owners-manual-2015-07-01.pdf",
    use: "Do not cross water deeper than 2.5 cm: the mobility scooter's limit.",
  },
  {
    citation: "Pride Mobility Products (2015). Go-Go Elite Traveller specification sheet (UK).",
    url: "https://www.pridemobility.com/pdf/brochures/uk/uk_gogo_elite_traveller_ss.pdf",
    use: "3.5 cm ground clearance at the motor of a travel scooter.",
  },
  {
    citation: "Pride Mobility, V10 and Pathrider 10 DX owner's manuals; Pride and Quantum wheelchair FAQs.",
    use: "Avoid standing water; do not climb kerbs higher than 5 cm.",
  },
  {
    citation: "Sunrise Medical. QUICKIE Nitrum order form (UK).",
    url: "https://www.vivid.care/wp-content/uploads/2022/10/Quickie-Nitrum.pdf",
    use: "Front castors of 3 to 6 inches; a castor's axle sits at half its diameter (5.1 cm for 4 inches, 7.6 cm for 6 inches).",
  },
  {
    citation: "Sunrise Medical. QUICKIE Q500 M brochure.",
    use: "3 inches (7.6 cm) of ground clearance on a powered wheelchair.",
  },
  {
    citation: "Permobil. M3 Corpus specifications.",
    url: "https://www.permobil.com/en-au/products/power-wheelchairs/permobil-m3-corpus",
    use: "About 75 mm of ground clearance on a powered wheelchair.",
  },
  {
    citation: "Invacare (2014). Storm⁴ power wheelchair user manual.",
    url: "https://finnhjelpemiddel.nav.no/imageproxy/file/brugsvejl/44776.pdf",
    use: "Electrics tested to IPX4 (EN 60529): splashing water, not immersion. Dynamic stability 6° (10.5%) under ISO 7176-2: more than 1:14, which is still applied to powered chairs (a judgement).",
  },
];

/** Basis of each body part a walker can choose, by its API key. */
export const BODY_PART_BASIS: Record<string, Basised> = {
  no_wading: { basis: "Chosen", note: "A film of water any pavement carries in rain; deeper water counts as wading." },
  ankle: { basis: "Cited", note: "0.039 × height (Drillis & Contini, 1966)." },
  lower_calf: { basis: "Derived", note: "A third of the way from ankle to knee." },
  mid_calf: { basis: "Derived", note: "Halfway between ankle and knee." },
  knee: { basis: "Cited", note: "0.285 × height (Drillis & Contini, 1966); capped at 50 cm." },
};

/** Basis of each mobility aid level, by "device/level" API keys. */
export const AID_LEVEL_BASIS: Record<string, Basised> = {
  "manual_wheelchair/no_water": { basis: "Chosen", note: "The same dry-pavement allowance as walkers; manufacturers advise avoiding standing water." },
  "manual_wheelchair/below_castor_axle": { basis: "Derived", note: "Axle of a 4-inch front castor (5.1 cm); also the 5 cm kerb limit in Pride's manuals." },
  "manual_wheelchair/below_large_castor_axle": {
    basis: "Chosen",
    note: "Axle of a 6-inch castor (7.6 cm). No source sets a wading depth for a manual wheelchair.",
  },
  "powered_wheelchair/no_water": { basis: "Chosen", note: "The same dry-pavement allowance as walkers." },
  "powered_wheelchair/below_chassis": {
    basis: "Chosen",
    note: "2.5 cm below about 7.5 cm of ground clearance, with electrics rated only for splashing water; the margin is a judgement.",
  },
  "mobility_scooter/no_water": { basis: "Chosen", note: "The same dry-pavement allowance as walkers." },
  "mobility_scooter/shallow_puddle": { basis: "Cited", note: "The one depth a manufacturer states (MinnieMobil); below a travel scooter's 3.5 cm motor clearance." },
};

export const HARD_LIMIT_NOTE =
  "Melbourne Water's Southbank plan takes up to 500 mm as safe pedestrian access, and 0.5 m is the H2 depth limit for people (Smith, Davey & Cox, 2014). Thigh and waist are not offered: they would be capped to 50 cm for almost everyone.";

export const AID_CAP_NOTE =
  "No study measures how stable an occupied wheelchair or scooter is in floodwater, so the levels follow the devices and their manufacturers, far below the 50 cm for walkers.";

export const LIMITS: string[] = [
  "The flood scenarios are a static estimate from ground height and published water levels, not a hydraulic model: there is no flow, velocity, timing or drain capacity.",
  "Rain-driven surcharge at a normal tide is missed, because pit and pipe levels are not published; a short storm can leave deeper water than the light flooding scenario shows.",
  "River levels are the bay's tide levels; river flows can raise them, so river depths are a lower bound.",
  "Every building with a way in counts as a shelter; whether it is open to the public is not known from the data.",
  "Gradients are known only where the City of Melbourne has surveyed the footpath (about two thirds of footpath length in Southbank); a path without one, such as a carriageway or a private path, is not treated as steep, and a route's steepest and gentlest gradient cover only its measured parts.",
  "A footpath section's gradient is an average between its lowest and highest points, so a short steep part of a long section can be missed; sections that seem to join two levels (at bridges and overpasses) are left out.",
];
