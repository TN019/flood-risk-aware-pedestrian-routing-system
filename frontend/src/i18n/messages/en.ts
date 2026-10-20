// The web client's text in English: the source for every other language. Each catalogue has the
// same keys (checked by TypeScript) and the same {placeholders} and numbers (checked by
// i18n.test.ts). Text the API composes (labels, depth descriptions, errors, scenarios) comes from
// the API in the chosen language; see backend/src/floodroute/api/locales. Conventions and the
// glossary for translators: docs/languages.md.

export const en = {
  // ---------------------------------------------------------------- shared
  "language.label": "Language",
  "app.title": "Southbank Flood Routes",
  "unit.min": "{count} min",
  "depth.unknown": "unknown",
  "depth.none": "none",
  "depth.withLabel": "{depth} ({label})",
  "route.recommended": "Recommended",
  "route.safe_shortest": "Shortest within your limit",
  "route.shortest": "Shortest, ignoring flooding",
  "route.downgrade": "With a higher limit",
  "route.refuge": "To shelter",
  "route.least_water": "Least water",
  "error.unreachable": "Cannot reach the routing service. Check your connection and try again.",
  "error.status": "The routing service returned an error ({status}).",

  // ---------------------------------------------------------------- the app: panel
  "app.tagline": "Walking routes that avoid water deeper than you choose to walk through.",
  "app.panel": "Trip planner",
  "app.sheetMore": "Show more map",
  "app.sheetDetails": "Show details",
  "app.loadError": "Could not load the map data.",
  "app.planError": "Could not plan this trip.",
  "app.planning": "Planning…",
  "app.safety":
    "Routes are guidance based on modelled conditions, which can be incomplete or wrong, and floods change quickly. Never walk through floodwater you do not have to, follow directions from emergency services, and in an emergency call 000 (VICSES 132 500 for flood or storm help).",
  "app.credits": "Map data © OpenStreetMap contributors. Flood scenarios: see Sources under each level.",
  // The pill on the map: "Next click sets the start" / "… the destination".
  "app.nextClick": "Next click sets the {target}",
  "app.nextClick.start": "start",
  "app.nextClick.destination": "destination",

  "trip.label": "Start and destination",
  "trip.start": "Start",
  "trip.destination": "Destination",
  "trip.locate": "Use my current location",
  "trip.swap": "Swap",
  "trip.clear": "Clear",
  "trip.hint": "Search for a place, or click the map: the first click sets the start, the next the destination.",
  "trip.outside": "Pick a point inside Southbank (the black boundary).",
  "trip.placeOutside": "{place} is outside Southbank.",
  "trip.noGeolocation": "Location is not available in this browser. Click the map to set your start instead.",
  "trip.locating": "Finding your location…",
  "trip.locationOutside": "Your location is outside Southbank. Click the map to set a simulated current location instead.",
  "trip.locationFailed": "Location unavailable (permission denied or not supported). Click the map to set your start instead.",
  "trip.yourLocation": "Your location",
  "trip.pointOnMap": "Point on the map",
  "trip.pointAt": "{place} ({lat}, {lon})",

  "search.onMap": "Set on map",
  "search.onMapActive": "Next map click sets this",
  "search.change": "Change",
  "search.placeholder": "e.g. Eureka Tower, 1 City Road",
  "search.button": "Search",
  "search.tooShort": "Type at least three letters.",
  "search.failed": "Search failed.",
  "search.noMatch": "No match inside Southbank. Try another name, or click the map.",

  // ---------------------------------------------------------------- flood conditions
  "conditions.title": "Flood conditions",
  "conditions.group": "Flood scenario",
  "conditions.none": "None",
  "conditions.over": "over {depth}",
  // {range}: where the water reaches, from the API, e.g. "up to an adult's ankle"; {depth} is bold.
  "conditions.water":
    "Water {range} ({band} for a {height} cm adult). Typical depth on flooded footpaths here: {depth}.",
  "conditions.dry": "No standing water.",
  "conditions.sources": "Sources",

  // ---------------------------------------------------------------- the traveller
  "you.title": "You",
  "you.height": "Height",
  "you.aid": "Mobility aid",
  "you.aidNone": "None",
  // {aid}: the device, from the API, e.g. "manual wheelchair".
  "you.aidDepth": "Deepest water for your {aid}",
  "you.aidNote":
    "Limits for wheeled aids follow the device (castor axle, chassis, manufacturer advice), not your height. Routes never use steps or footpaths measured steeper than 1:14.",
  "you.wading": "Deepest water you will walk through",
  "you.limit": "Your limit: {limit}",
  "you.cap": "(never more than {cap})",
  "you.preference": "Route preference",
  "you.preferenceNote":
    "Water deeper than your limit is always avoided; this only decides whether water within it is worth walking around.",
  "you.advanced": "Advanced",
  "you.alpha": "Risk weight α: {alpha}",
  "you.alphaNote": "Extra metres worth walking to avoid one metre of water right at your limit.",
  "you.alphaBack": "Back to the preference",

  // ---------------------------------------------------------------- trip results
  "origin.unknownWater": "water of unknown depth",
  "origin.water": "{depth} of water",
  "origin.overLimit": "You are standing in {water} ({label}), deeper than your limit.",
  "origin.deep": "You are standing in {water} ({label}). Move carefully; help is available.",
  "origin.veryDeep": "The water here is {depth} deep, above your knee. Calling for help is recommended before moving.",
  "origin.criticalUnknown": "The depth here is unknown.",
  "origin.critical": "The water here is {depth} deep ({label}).",
  "origin.criticalAction": "Stay where you are if you can and call for help now.",

  "emergency.title": "Emergency help — {advice}",
  "emergency.available": "available",
  "emergency.recommended": "recommended",
  "emergency.stronglyRecommended": "strongly recommended",
  "emergency.onlyOption": "your only option",
  "emergency.cutOff": "You are cut off by deep water. Stay inside, and move to a higher floor if water comes into the building.",
  "emergency.note": "000 if anyone's life is in danger; VICSES for flood help, such as being trapped or water coming in.",

  "compare.title": "Compare routes",
  "compare.notSafe": "not safe",
  "compare.deepest": "Deepest {depth} · {water} in water",
  "compare.overLimit": "{count} section(s) over your limit",
  "compare.hint": "Select a route to see it on the map.",
  "compare.blocked": "{count} network sections are over your limit in this scenario.",
  "access.avoidsSteps": "Every route avoids the steps on the shortest way.",
  "access.avoidsSteep": "Every route avoids the paths steeper than 1:14 on the shortest way.",
  "access.avoidsBoth": "Every route avoids the steps and the paths steeper than 1:14 on the shortest way.",
  "access.stepFree": "Every route is step-free.",
  "gradient.none": "No gradient data",
  "gradient.one": "Gradient {gradient}",
  "gradient.range": "Gradient {from} to {to}",
  "trip.fromTo": "From {from} to {to}.",
  "trip.selectedPoint": "the selected point",
  "trip.placeAccess": "{place} ({access})",

  // ---------------------------------------------------------------- the next step card
  "next.label": "Next step",
  "next.go": "You can go: this route stays within your limit",
  "next.detour": "Take the recommended route",
  "next.choose": "No route keeps you within your limit. Choose one:",
  "next.downgrade": "No route keeps you within your limit",
  "next.shelterCritical": "Stay where you are if you can and call for help",
  "next.shelterFold": "If you cannot wait for help: the way to shelter",
  "next.shelter": "Go to a shelter and wait",
  "next.stay": "Stay inside {place} until the water goes down",
  "next.help": "No safe way out from here: call for help",
  "next.helpBody": "No shelter can be reached. Stay on the highest ground you can reach.",
  "next.unreachable": "No route connects these points",
  "next.show": "Show on the map",
  "next.shown": "Shown on the map",
  // {water}: from the API, e.g. "water up to the knee", "a shallow puddle".
  "next.accept": "Accept {water} ({depth})",
  "next.useLimit": "Use this limit",
  "next.refuge": "Wait at a shelter: {name}",
  // {entrance}: from the API, e.g. "main entrance".
  "next.refugeWay": "To the {entrance}: {route}. Wait there until the water goes down.",
  "next.refugeOverLimit": "The way there crosses water deeper than your limit; it is the shallowest way out.",
  "next.stayInside": "Stay inside {place}",
  "next.wait": "Wait until the water goes down.",
  "next.leastWater": "The way with the least water",
  "next.routeLine": "{distance} · {time} · deepest {depth}",
  "metric.walk": "walk",
  "metric.vsShortest": "+{percent}% vs shortest",
  "metric.estimated": "estimated",
  "metric.unknown": "Unknown",
  "metric.dry": "Dry",
  "metric.deepest": "deepest water",
  "metric.inWater": "in water",
  "metric.steepest": "steepest",
  "metric.gentlest": "gentlest",
  "metric.noGradient": "no gradient data",

  // Why no route fits: {depth} and {limit} are depths such as "32 cm", {label} where the water
  // reaches (from the API), {aid} the traveller's device and {place} the destination's name.
  "why.unknown": "Every way there crosses water of unknown depth.",
  "why.unknownTo": "Every way to {place} crosses water of unknown depth.",
  "why.overLimit":
    "Every way there crosses at least {depth} of water ({label}), deeper than your limit of {limit}. The deepest point is marked on the map.",
  "why.overLimitTo":
    "Every way to {place} crosses at least {depth} of water ({label}), deeper than your limit of {limit}. The deepest point is marked on the map.",
  "why.overCap":
    "Every way there crosses at least {depth} of water ({label}), more than the {limit} anyone is routed through. The deepest point is marked on the map.",
  "why.overCapTo":
    "Every way to {place} crosses at least {depth} of water ({label}), more than the {limit} anyone is routed through. The deepest point is marked on the map.",
  "why.overAidCap":
    "Every way there crosses at least {depth} of water ({label}), more than the {limit} a {aid} is routed through. The deepest point is marked on the map.",
  "why.overAidCapTo":
    "Every way to {place} crosses at least {depth} of water ({label}), more than the {limit} a {aid} is routed through. The deepest point is marked on the map.",
  // What the recommended route gains over the shortest way: {distance}, {extra} and {water} are
  // distances such as "120 m".
  "detour.unknown":
    "The shortest way ({distance}) crosses water of unknown depth. This route walks {extra} further to stay within it.",
  "detour.overLimit":
    "The shortest way ({distance}) crosses water deeper than your limit, up to {depth} ({label}). This route walks {extra} further to stay within it.",
  "detour.avoid": "This route walks {extra} further than the shortest way to avoid {water} of water up to {depth} ({label}).",

  // ---------------------------------------------------------------- map and legend
  "map.label": "Map of Southbank",
  "map.unknownDepth": "Depth unknown · treated as too deep",
  "map.overLimit": "over your limit",
  "map.shelter": "Shelter: {name}",
  "map.deepest": "Deepest point on the least-water route: {depth}",
  "map.deepestUnknown": "Deepest point on the least-water route: unknown depth",
  "map.failed": "The map stopped drawing.",
  "map.failedWhy": "The browser ran out of graphics resources.",
  "map.reload": "Reload map",
  "map.failedNote": "If this keeps happening, quit and reopen the browser.",
  "map.zoomIn": "Zoom in",
  "map.zoomOut": "Zoom out",
  "map.attribution": "Toggle attribution",
  "legend.title": "Legend",
  "legend.waterOk": "Water within your limit",
  "legend.waterOver": "Over your limit or unknown",
  "legend.shortestUnsafe": "Shortest, ignoring flooding (not safe)",
  // {label}: a body part from the API, e.g. "knee".
  "legend.downgradeBody": "With a {label} limit",
  "legend.downgradeAid": "With a higher limit ({depth})",
  "legend.deepest": "Deepest point on the least-water route",

  // ---------------------------------------------------------------- getting help
  "help.button": "Get help",
  "help.close": "Close",
  "help.call000": "Call 000",
  "help.lifeDanger": "If anyone's life is in danger.",
  "help.ses": "Flood or storm help: trapped by water, water coming inside, a fallen tree.",
  "help.simulated": "Calls open your phone's dialler. The SOS alert is simulated in this version.",
  "sos.button": "Alert people nearby (SOS)",
  "sos.sent": "SOS sent {seconds} s ago with {shared} (simulated).",
  "sos.undo": "Undo ({seconds} s)",
  // What an SOS shares, put into "SOS sent … with {shared}".
  "sos.noLocation": "no location (set a start to share one)",
  "sos.currentLocation": "your current location",
  "sos.startAsLocation": "your start point as your location",
  "sos.here": "your location",
  "sos.hereWithDepth": "your location and {depth} water depth",

  // ---------------------------------------------------------------- shared by /reference and /benchmark
  "doc.back": "← Southbank Flood Routes",
  "doc.sections": "Sections",
  "basis.cited": "Cited",
  "basis.derived": "Derived",
  "basis.chosen": "Judgement",
  "basis.chosenTitle": "A judgement",

  // ---------------------------------------------------------------- /reference
  "ref.title": "Sources and references",
  "ref.pageTitle": "Sources and references · Southbank Flood Routes",
  "ref.intro":
    "Where the map, the network and the flood scenarios come from, and what every depth limit rests on. The values in the tables are read from the running system, so they are the ones routes use.",
  "ref.nav.data": "Data",
  "ref.nav.scenarios": "Flood scenarios",
  "ref.nav.limits": "Depth limits",
  "ref.nav.documents": "Documents",
  "ref.nav.licences": "Licences",
  "ref.nav.notCovered": "Not covered",
  "ref.data.title": "Data",
  "ref.data.data": "Data",
  "ref.data.use": "Used for",
  "ref.data.licence": "Licence",
  "ref.scenarios.title": "Flood scenarios",
  "ref.scenarios.intro":
    "Each scenario is a published water level applied to the ground model: river and storm tide, drains backing up at high tide, and rain ponding in low spots. Its flood level is set by the typical depth on flooded footpaths.",
  "ref.scenarios.typical": "typical depth {depth}",
  "ref.limits.title": "Depth limits",
  "ref.limits.cited": "taken from a named source.",
  "ref.limits.derived": "worked out from cited values.",
  "ref.limits.chosen": "no source sets the value, so it is chosen; these are the first to revisit when better evidence appears.",
  "ref.loading": "Loading the current values…",
  "ref.loadError": "The current values could not be loaded: {error}",
  "ref.walking": "Walking",
  "ref.walkingIntro":
    "Travellers choose the deepest water they will walk through as a part of the body; it becomes a depth from their height. Depths below are for a {height} cm adult.",
  "ref.choice": "Choice",
  "ref.depth": "Depth",
  "ref.basis": "Basis",
  "ref.fraction": "({fraction} × height)",
  "ref.upperLimit": "Upper limit for everyone",
  "ref.atMost": "at most {depth}",
  "ref.aids": "Wheelchairs and mobility scooters",
  "ref.aidsIntro":
    "Travellers with a wheeled mobility aid choose a level of their device instead, and are never routed over steps or paths steeper than 1:14, the steepest ramp AS 1428.1 allows. Every route shows its steepest and gentlest measured gradient.",
  "ref.deviceLevel": "Device and level",
  "ref.cap": "(cap)",
  "ref.levels": "Flood levels",
  "ref.levelsIntro":
    "The four levels are named by where the typical water reaches on a {height} cm adult: the ankle, knee and hip waterlines used to grade flood severity (Feng, Brenner & Sester, 2020), with body heights from Drillis & Contini (1966).",
  "ref.level": "Level",
  "ref.typicalWater": "Typical water",
  "ref.over": "over {depth}",
  "ref.seeParameters": "See docs/parameters.md",
  "ref.documents.title": "Documents",
  "ref.documents.flooding": "Flooding in Southbank",
  "ref.documents.people": "People in floodwater and access",
  "ref.documents.mobility": "Wheelchairs and mobility scooters",
  "ref.documents.note": "Citations are given in their original language.",

  "ref.licences.title": "Licences",
  "ref.licences.software": "The software is licensed under the {licence}.",
  "ref.licences.osm":
    "Data derived from OpenStreetMap, such as the processed walking network, is available under the {licence} and credits © OpenStreetMap contributors.",
  "ref.licences.others": "The other datasets keep the licences listed above. The documents are cited, not redistributed.",
  "ref.notCovered.title": "Not covered",
  "ref.notCovered.notice":
    "This is not an official flood warning service. Follow warnings from VICSES and the Bureau of Meteorology, call 000 in an emergency, and call VICSES on 132 500 for flood or storm help.",
  "ref.footer": "Every parameter, where it is set and why: {parameters}. How the system works: {architecture}.",

  // What each dataset is used for (its name, publisher and licence stay as published).
  "ref.data.osm.name": "Walking network, buildings and entrances",
  "ref.data.osm.use": "The paths routes follow, steps, the buildings used as start, destination and shelter, and their entrances.",
  "ref.data.clue.use": "The Southbank boundary, the area the system covers.",
  "ref.data.pits.use": "Drain inlets that open to the surface, where a high tide backs up through the drains.",
  "ref.data.steepness.use":
    "The gradient of each council footpath section: every route shows its steepest and gentlest measured gradient, and wheelchair and scooter routes leave out paths steeper than 1:14.",
  "ref.data.pedestrian.use": "An alternative walking network, used to check the OpenStreetMap one.",
  "ref.data.dem.use": "Ground height, from which the depth of water at every point is worked out.",
  "ref.data.overlays.use": "Land expected to flood in a 1-in-100-year event; shown for context in the Streamlit app, not used for routing.",
  "ref.data.search.name": "Place search",
  "ref.data.search.use": "Finding a place typed into the search boxes.",
  "ref.data.basemap.name": "Basemap",
  "ref.data.basemap.use": "The map drawn under the routes; OpenStreetMap's own tiles if it does not load.",
  "ref.data.census.use":
    "The languages this site is offered in: those most used at home in Southbank (SAL22315) and Southbank (West) – South Wharf (SA2 206041508).",

  // What each document is used for (the citation stays as published).
  "ref.doc.melbourneWater.use":
    "How Southbank floods (storm tide and river flows, local stormwater, drains that cannot discharge at high tide); 500 mm as safe pedestrian access, 300 mm for vulnerable uses.",
  "ref.doc.ghd.use":
    "Storm tide levels for Port Phillip Bay (Table 1): 1-in-20-year 1.25 m, 1-in-100-year 1.60 m, 1-in-100-year in 2100 2.40 m AHD.",
  "ref.doc.waterTechnology.use": "Highest astronomical tide at Williamstown, 0.59 m AHD (Table 2-1): the light flooding level.",
  "ref.doc.floodSubPlan.use": "A high tide reduces the drains' capacity and backflow surcharges around the pits.",
  "ref.doc.floodGuide.use": "Streets expected to flood at the Southbank gauge, used to check the scenarios; the gauge's major flood level.",
  "ref.doc.vpp.use": "Planning for 0.8 m of sea level rise by 2100: the extreme flooding level.",
  "ref.doc.drillis.use": "Ankle, knee and hip heights as fractions of a person's height.",
  "ref.doc.feng.use": "Ankle, knee and hip as the waterlines that grade how severe a flood is: the boundaries of the four flood levels.",
  "ref.doc.smith.use": "0.5 m as the depth limit for people (H2) and children's wading limit; vulnerable people should avoid flowing floodwater.",
  "ref.doc.abs.use": "Average adult height, 1.69 m: the 1.70 m reference adult used to describe the flood levels.",
  "ref.doc.as1428.use":
    "An accessible path of travel has no steps and no ramp steeper than 1:14 (kerb ramps up to 1:8 over 1.52 m), so wheelchair and scooter routes use neither.",
  "ref.doc.minniemobil.use": "Do not cross water deeper than 2.5 cm: the mobility scooter's limit.",
  "ref.doc.pride.use": "3.5 cm ground clearance at the motor of a travel scooter.",
  "ref.doc.prideManuals.use": "Avoid standing water; do not climb kerbs higher than 5 cm.",
  "ref.doc.nitrum.use": "Front castors of 3 to 6 inches; a castor's axle sits at half its diameter (5.1 cm for 4 inches, 7.6 cm for 6 inches).",
  "ref.doc.q500.use": "3 inches (7.6 cm) of ground clearance on a powered wheelchair.",
  "ref.doc.permobil.use": "About 75 mm of ground clearance on a powered wheelchair.",
  "ref.doc.invacare.use":
    "Electrics tested to IPX4 (EN 60529): splashing water, not immersion. Dynamic stability 6° (10.5%) under ISO 7176-2: more than 1:14, which is still applied to powered chairs (a judgement).",

  // The basis of each limit.
  "ref.basis.no_wading": "A film of water any pavement carries in rain; deeper water counts as wading.",
  "ref.basis.ankle": "0.039 × height (Drillis & Contini, 1966).",
  "ref.basis.lower_calf": "A third of the way from ankle to knee.",
  "ref.basis.mid_calf": "Halfway between ankle and knee.",
  "ref.basis.knee": "0.285 × height (Drillis & Contini, 1966); capped at 50 cm.",
  "ref.basis.manualNoWater": "The same dry-pavement allowance as walkers; manufacturers advise avoiding standing water.",
  "ref.basis.castorAxle": "Axle of a 4-inch front castor (5.1 cm); also the 5 cm kerb limit in Pride's manuals.",
  "ref.basis.largeCastorAxle": "Axle of a 6-inch castor (7.6 cm). No source sets a wading depth for a manual wheelchair.",
  "ref.basis.sameAsWalkers": "The same dry-pavement allowance as walkers.",
  "ref.basis.belowChassis":
    "2.5 cm below about 7.5 cm of ground clearance, with electrics rated only for splashing water; the margin is a judgement.",
  "ref.basis.shallowPuddle": "The one depth a manufacturer states (MinnieMobil); below a travel scooter's 3.5 cm motor clearance.",
  "ref.basis.hardLimit":
    "Melbourne Water's Southbank plan takes up to 500 mm as safe pedestrian access, and 0.5 m is the H2 depth limit for people (Smith, Davey & Cox, 2014). Thigh and waist are not offered: they would be capped to 50 cm for almost everyone.",
  "ref.basis.aidCap":
    "No study measures how stable an occupied wheelchair or scooter is in floodwater, so the levels follow the devices and their manufacturers, far below the 50 cm for walkers.",

  // What the system does not cover.
  "ref.limit.static":
    "The flood scenarios are a static estimate from ground height and published water levels, not a hydraulic model: there is no flow, velocity, timing or drain capacity.",
  "ref.limit.surcharge":
    "Rain-driven surcharge at a normal tide is missed, because pit and pipe levels are not published; a short storm can leave deeper water than the light flooding scenario shows.",
  "ref.limit.river": "River levels are the bay's tide levels; river flows can raise them, so river depths are a lower bound.",
  "ref.limit.shelters": "Every building with a way in counts as a shelter; whether it is open to the public is not known from the data.",
  "ref.limit.gradients":
    "Gradients are known only where the City of Melbourne has surveyed the footpath (about two thirds of footpath length in Southbank); a path without one, such as a carriageway or a private path, is not treated as steep, and a route's steepest and gentlest gradient cover only its measured parts.",
  "ref.limit.sections":
    "A footpath section's gradient is an average between its lowest and highest points, so a short steep part of a long section can be missed; sections that seem to join two levels (at bridges and overpasses) are left out.",

  // ---------------------------------------------------------------- /benchmark
  "bench.title": "Benchmarks",
  "bench.pageTitle": "Benchmarks · Southbank Flood Routes",
  "bench.intro":
    "Whether routes follow their rules on the data they are given, checked automatically on made-up data (a small test town) and on the real Southbank network. The predictions were written before the first run, in {benchmarks}.",
  "bench.run": "Run {date} on commit {commit}; network of {nodes} junctions and {edges} sections.",
  "bench.unknownCommit": "unknown",
  "bench.loadError": "The benchmark results could not be loaded: {error}",
  "bench.loading": "Loading the results…",
  "bench.footer": "Run them again with {command} in {folder}; the results are written to {file}.",
  "bench.measured": "Measured",
  "bench.asPredicted": "As predicted",
  "bench.notAsPredicted": "Not as predicted",
  "bench.share": "{count} of {total}",
  "bench.none": "none",
  "bench.yes": "Yes",
  "bench.no": "No",
  "bench.algorithm": "Algorithm layer",
  "bench.correctness": "Correctness",
  "bench.pathFinder": "Path finder against NetworkX",
  "bench.pathFinderText":
    "Node to node: same cost for {pairs} random pairs ({same} with the identical path). Through the router, with snapping and access legs: same length for {routes} random trips.",
  "bench.minimax": "Safest-path search against brute force",
  "bench.minimaxText":
    "The lowest possible deepest point, then the shortest path that deep, agreed with enumerating every path for {pairs} node pairs on {graphs} random graphs.",
  "bench.predictions": "Hand-derived predictions",
  "bench.predictionsText": "Test town cases A–J: {town} met. Southbank properties R-A to R-I: {southbank} met.",
  "bench.faults": "Fault injection",
  "bench.faultsText":
    "Each fault breaks one safety rule on purpose; the whole test suite then runs against the broken code. As written, the suite has {failed} failures in {tests} tests.",
  "bench.fault": "Fault",
  "bench.testsFailed": "Tests failed",
  "bench.casesFailed": "Test town cases failed",
  "bench.caught": "Caught",
  "bench.safety": "Pedestrian safety",
  "bench.cost": "Safety and what it costs",
  "bench.costText":
    "{trips} random trips at each flood level. No recommended route crossed water over the traveller's limit in {plans} plans{overLimit}. Where the plain shortest way crosses water over the limit, the recommended route is longer by the median shown and avoids the median length of water over the limit.",
  "bench.costOverLimit": " ({count} did)",
  "bench.levelTraveller": "Level and traveller",
  "bench.withRoute": "Route within the limit",
  "bench.shortestUnsafe": "Shortest way unsafe",
  "bench.longerBy": "Longer by",
  "bench.avoided": "Water over the limit avoided",
  "bench.offered": "Without a route, offered",
  "bench.rising": "Rising flood: rerouting on the way",
  "bench.risingText":
    "{trips} trips for an {traveller} traveller walking while the flood rises: {schedule}. At every rise the trip is planned again from where they are.",
  "bench.risingFrom": "{level} from {minutes} min",
  "bench.risingViolations": "Walked in water over the limit on a route given as within it: {metres}.",
  "bench.risingReroutes":
    "Rerouted {reroutes} times, in {trips} trips; {caught} times the water had risen over the limit where they stood, and the safest way out crossed {metres} of it in all.",
  "bench.risingOutcomes": "Outcomes: {outcomes}.",
  "bench.risingExtra": "Arrivals walked {median} further than first planned (median; 90th percentile {p90}).",
  "bench.finding": "Finding:",
  "bench.findingText":
    "{count} times the flood rose while the route ran through the network's margin outside Southbank, where no trip can be planned (a start must lie inside). The traveller kept to the route they had and walked {metres} over the limit there in all. Replanning should work from anywhere on the network a route can take.",
  "bench.access": "Public area accessibility",
  "bench.stepFree": "Step-free connectivity between buildings",
  "bench.stepFreeText":
    "{pairs} random pairs of buildings connected on foot, normal conditions. The step-free route also leaves out paths steeper than 1:14, which {steep} of the walking routes use. A step-free route exists for {routes}, and for {same} it is the walking route itself (no steps or steep paths on the way). Over all pairs it is longer by {median} at the median, {p90} at the 90th percentile and {max} at most. No step-free route uses steps ({steps}) or a path steeper than 1:14 ({steepUsed}), or costs less than the walking route ({cheaper}).",
  "bench.stepFreeShorter.one":
    "{count} is shorter in metres but costs more: routes minimise walking cost, with a carriageway counted three times its length.",
  "bench.stepFreeShorter.other":
    "{count} are shorter in metres but cost more: routes minimise walking cost, with a carriageway counted three times its length.",
  // The benchmark's travellers, outcomes and faults (docs/benchmark.json writes them in English).
  "bench.traveller.adultAnkle": "adult, ankle",
  "bench.traveller.adultMidCalf": "adult, mid calf",
  "bench.traveller.childMidCalf": "child, mid calf",
  "bench.traveller.manualWheelchair5": "manual wheelchair, 5 cm",
  "bench.outcome.arrived": "arrived",
  "bench.outcome.atShelter": "at a shelter",
  "bench.outcome.higherLimit": "higher limit",
  "bench.outcome.shelter": "shelter",
  "bench.outcome.stayInside": "stay inside",
  "bench.outcome.emergencyHelp": "emergency help",
  "bench.outcome.notConnected": "not connected",
  "bench.outcome.nothing": "nothing",
  "bench.fault.F1": "Water deeper than the limit is passable",
  "bench.fault.F2": "Water of unknown depth counts as dry",
  "bench.fault.F3": "No 50 cm hard limit for walkers",
  "bench.fault.F4": "Wheelchair users may use steps",
  "bench.fault.F5": "No refuge is offered",
  "bench.fault.F6": "No downgrade is offered",
  "bench.fault.F7": "No emergency help when cut off inside a building",
  "bench.fault.F8": "No emergency help at all",
  "bench.fault.F9": "The recommended route ignores water within the limit (α = 0)",
  "bench.fault.F10": "Mobility aid users may use paths steeper than 1:14",
};

export type Messages = Record<keyof typeof en, string>;
export type MessageKey = keyof typeof en;
