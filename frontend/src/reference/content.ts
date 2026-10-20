// What the /reference page says about the data, the documents and the judgement values behind the
// routes. The numbers themselves come from the API, so they cannot drift from the engine; the text
// here must be kept in step with README.md (Data sources), NOTICE and docs/parameters.md.
//
// Dataset names, publishers, licences and citations stay as published, in English; what they are
// used for and the notes are in the catalogues (i18n/messages), by key.

import type { MessageKey } from "../i18n/messages/en";

export interface Dataset {
  name: string;
  nameKey?: MessageKey; // a description rather than a published name, so it is translated
  publisher: string;
  use: MessageKey;
  licence: string;
  url?: string;
  licenceUrl?: string;
}

export interface Work {
  citation: string;
  use: MessageKey;
  url?: string;
}

/** How a value was reached, as in docs/parameters.md. "Chosen" values are judgements. */
export type Basis = "Cited" | "Derived" | "Chosen";

export interface Basised {
  basis: Basis;
  note: MessageKey;
}

const CC_BY_4 = "https://creativecommons.org/licenses/by/4.0/";

export const DATASETS: Dataset[] = [
  {
    name: "Walking network, buildings and entrances",
    nameKey: "ref.data.osm.name",
    publisher: "© OpenStreetMap contributors, through the Overpass API and OSMnx",
    use: "ref.data.osm.use",
    licence: "ODbL 1.0",
    url: "https://www.openstreetmap.org/copyright",
    licenceUrl: "https://opendatacommons.org/licenses/odbl/1-0/",
  },
  {
    name: "Small Areas for Census of Land Use and Employment (CLUE)",
    publisher: "City of Melbourne",
    use: "ref.data.clue.use",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/small-areas-for-census-of-land-use-and-employment-clue/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Stormwater Pits",
    publisher: "City of Melbourne",
    use: "ref.data.pits.use",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/stormwater-pits/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Footpath steepness",
    publisher: "City of Melbourne",
    use: "ref.data.steepness.use",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/footpath-steepness/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Pedestrian Network",
    publisher: "City of Melbourne",
    use: "ref.data.pedestrian.use",
    licence: "CC BY 4.0",
    url: "https://data.melbourne.vic.gov.au/explore/dataset/pedestrian-network/",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Digital Elevation Model (DEM) of Australia derived from LiDAR 5 Metre Grid",
    publisher: "© Commonwealth of Australia (Geoscience Australia), through its 2025 web service",
    use: "ref.data.dem.use",
    licence: "CC BY 4.0",
    url: "https://doi.org/10.26186/89644",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Vicmap Planning, Planning Scheme Overlay Polygon (LSIO, SBO, FO)",
    publisher: "© State of Victoria (Department of Transport and Planning)",
    use: "ref.data.overlays.use",
    licence: "CC BY 4.0",
    url: "https://discover.data.vic.gov.au/dataset/vicmap-planning-planning-scheme-overlay-polygon",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Census of Population and Housing 2021, QuickStats: Language used at home",
    publisher: "Australian Bureau of Statistics",
    use: "ref.data.census.use",
    licence: "CC BY 4.0",
    url: "https://abs.gov.au/census/find-census-data/quickstats/2021/SAL22315",
    licenceUrl: CC_BY_4,
  },
  {
    name: "Place search",
    nameKey: "ref.data.search.name",
    publisher: "OpenStreetMap Nominatim",
    use: "ref.data.search.use",
    licence: "ODbL 1.0; usage policy applies",
    url: "https://operations.osmfoundation.org/policies/nominatim/",
    licenceUrl: "https://opendatacommons.org/licenses/odbl/1-0/",
  },
  {
    name: "Basemap",
    nameKey: "ref.data.basemap.name",
    publisher: "OpenFreeMap (Positron style), OpenMapTiles schema, © OpenStreetMap contributors",
    use: "ref.data.basemap.use",
    licence: "ODbL 1.0 data; OpenMapTiles design CC BY 4.0",
    url: "https://openfreemap.org/",
    licenceUrl: "https://github.com/openmaptiles/openmaptiles/blob/master/LICENSE.md",
  },
];

export const FLOOD_DOCUMENTS: Work[] = [
  {
    citation: "Melbourne Water (2026). Southbank Precinct Local Floodplain Development Plan 2026.",
    url: "https://www.melbournewater.com.au/services/projects/southbank-precinct-flood-risk-and-development-planning",
    use: "ref.doc.melbourneWater.use",
  },
  {
    citation: "GHD (2017). Melbourne Water – Fishermans Bend: Baseline drainage plan options. Report 31/34157, prepared for Melbourne Water.",
    url: "https://www.vic.gov.au/sites/default/files/2024-11/GHD-Baseline-Drainage-Plan-Report.pdf",
    use: "ref.doc.ghd.use",
  },
  {
    citation:
      "Water Technology (2023). Erosion Hazard Summary Report – Port Phillip Bay Coastal Erosion Hazards. Report to the Department of Energy, Environment and Climate Action, part of the Port Phillip Bay Coastal Hazard Assessment.",
    url: "https://www.marineandcoasts.vic.gov.au/coastal-programs/port-phillip-bay-coastal-hazard-assessment",
    use: "ref.doc.waterTechnology.use",
  },
  {
    citation: "City of Melbourne Municipal Emergency Management Planning Committee and VICSES (2025). City of Melbourne Flood and Storm Sub-Plan, version 1.0.",
    url: "https://www.ses.vic.gov.au/documents/d/www/city-of-melbourne-memp-flood-and-storm-sub-plan",
    use: "ref.doc.floodSubPlan.use",
  },
  {
    citation: "VICSES (2021). Southbank Local Flood Guide.",
    url: "https://www.ses.vic.gov.au/plan-and-stay-safe/flood-guides/melbourne-city-council",
    use: "ref.doc.floodGuide.use",
  },
  {
    citation: "Victoria Planning Provisions, clause 13.01-2S Coastal inundation and erosion.",
    url: "https://planning-schemes.app.planning.vic.gov.au/Victoria%20Planning%20Provisions/ordinance/13.01-2S",
    use: "ref.doc.vpp.use",
  },
];

export const PEOPLE_DOCUMENTS: Work[] = [
  {
    citation:
      "Drillis, R. & Contini, R. (1966). Body segment parameters. Technical Report 1166-03, School of Engineering and Science, New York University.",
    use: "ref.doc.drillis.use",
  },
  {
    citation:
      "Feng, Y., Brenner, C. & Sester, M. (2020). Flood severity mapping from Volunteered Geographic Information by interpreting water level from images containing people: A case study of Hurricane Harvey. ISPRS Journal of Photogrammetry and Remote Sensing, 169, 301–319.",
    use: "ref.doc.feng.use",
    url: "https://doi.org/10.1016/j.isprsjprs.2020.09.011",
  },
  {
    citation: "Smith, G. P., Davey, E. K. & Cox, R. J. (2014). Flood Hazard. WRL Technical Report 2014/07, Water Research Laboratory, UNSW.",
    url: "https://www.unsw.edu.au/content/dam/pdfs/engineering/civil-environmental/water-research-laboratory/publications/WRL-TR2014-07-Flood-hazard.pdf",
    use: "ref.doc.smith.use",
  },
  {
    citation: "Australian Bureau of Statistics (2012). Australian Health Survey: First Results, 2011–12 (cat. no. 4364.0.55.001).",
    url: "https://www.abs.gov.au/AUSSTATS/abs@.nsf/DetailsPage/4364.0.55.0012011-12",
    use: "ref.doc.abs.use",
  },
  {
    citation: "Standards Australia (2021). AS 1428.1:2021 Design for access and mobility, Part 1: General requirements for access – New building work.",
    url: "https://store.standards.org.au/product/as-1428-1-2021",
    use: "ref.doc.as1428.use",
  },
];

export const MOBILITY_DOCUMENTS: Work[] = [
  {
    citation: "Minniemobil (2015). MM-01 / MM-02 mobility scooter owner's manual.",
    url: "https://minniemobil.com/wp-content/uploads/2015/07/minniemobil-mm-01-mm-02-owners-manual-2015-07-01.pdf",
    use: "ref.doc.minniemobil.use",
  },
  {
    citation: "Pride Mobility Products (2015). Go-Go Elite Traveller specification sheet (UK).",
    url: "https://www.pridemobility.com/pdf/brochures/uk/uk_gogo_elite_traveller_ss.pdf",
    use: "ref.doc.pride.use",
  },
  {
    citation: "Pride Mobility, V10 and Pathrider 10 DX owner's manuals; Pride and Quantum wheelchair FAQs.",
    use: "ref.doc.prideManuals.use",
  },
  {
    citation: "Sunrise Medical. QUICKIE Nitrum order form (UK).",
    url: "https://www.vivid.care/wp-content/uploads/2022/10/Quickie-Nitrum.pdf",
    use: "ref.doc.nitrum.use",
  },
  {
    citation: "Sunrise Medical. QUICKIE Q500 M brochure.",
    use: "ref.doc.q500.use",
  },
  {
    citation: "Permobil. M3 Corpus specifications.",
    url: "https://www.permobil.com/en-au/products/power-wheelchairs/permobil-m3-corpus",
    use: "ref.doc.permobil.use",
  },
  {
    citation: "Invacare (2014). Storm⁴ power wheelchair user manual.",
    url: "https://finnhjelpemiddel.nav.no/imageproxy/file/brugsvejl/44776.pdf",
    use: "ref.doc.invacare.use",
  },
];

/** Basis of each body part a walker can choose, by its API key. */
export const BODY_PART_BASIS: Record<string, Basised> = {
  no_wading: { basis: "Chosen", note: "ref.basis.no_wading" },
  ankle: { basis: "Cited", note: "ref.basis.ankle" },
  lower_calf: { basis: "Derived", note: "ref.basis.lower_calf" },
  mid_calf: { basis: "Derived", note: "ref.basis.mid_calf" },
  knee: { basis: "Cited", note: "ref.basis.knee" },
};

/** Basis of each mobility aid level, by "device/level" API keys. */
export const AID_LEVEL_BASIS: Record<string, Basised> = {
  "manual_wheelchair/no_water": { basis: "Chosen", note: "ref.basis.manualNoWater" },
  "manual_wheelchair/below_castor_axle": { basis: "Derived", note: "ref.basis.castorAxle" },
  "manual_wheelchair/below_large_castor_axle": { basis: "Chosen", note: "ref.basis.largeCastorAxle" },
  "powered_wheelchair/no_water": { basis: "Chosen", note: "ref.basis.sameAsWalkers" },
  "powered_wheelchair/below_chassis": { basis: "Chosen", note: "ref.basis.belowChassis" },
  "mobility_scooter/no_water": { basis: "Chosen", note: "ref.basis.sameAsWalkers" },
  "mobility_scooter/shallow_puddle": { basis: "Cited", note: "ref.basis.shallowPuddle" },
};

export const HARD_LIMIT_NOTE: MessageKey = "ref.basis.hardLimit";

export const AID_CAP_NOTE: MessageKey = "ref.basis.aidCap";

export const LIMITS: MessageKey[] = [
  "ref.limit.static",
  "ref.limit.surcharge",
  "ref.limit.river",
  "ref.limit.shelters",
  "ref.limit.gradients",
  "ref.limit.sections",
];
