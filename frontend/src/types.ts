// Shapes returned by the API (backend/src/floodroute/api/service.py).

export type Geometry = GeoJSON.Geometry;
export type FeatureCollection = GeoJSON.FeatureCollection;

export interface LatLon {
  lat: number;
  lon: number;
}

export interface Area {
  study_area: Geometry;
  routable_area: Geometry;
  bounds: [number, number, number, number]; // west, south, east, north
}

export interface BodyPartOption {
  key: string;
  label: string;
  fraction: number | null;
}

export interface PreferenceOption {
  key: string;
  label: string;
  summary: string;
  alpha: number;
}

export interface FloodLevel {
  key: string;
  label: string;
  body_range: string;
  lower_m: number;
  upper_m: number | null;
}

export interface AidLevel {
  key: string;
  label: string;
  depth_m: number;
}

export interface MobilityAidOption {
  key: string;
  label: string;
  levels: AidLevel[];
}

export interface Options {
  body_parts: BodyPartOption[];
  mobility_aids: MobilityAidOption[];
  landmarks: { fraction: number; name: string }[];
  dry_depth_m: number;
  hard_limit_m: number;
  max_gradient: number; // steepest path a mobility aid user is routed on (rise over run, 1:14)
  preferences: PreferenceOption[];
  default_preference: string;
  flood_levels: FloodLevel[];
  reference_height_m: number;
  sos_undo_seconds: number;
}

export interface ScenarioSummary {
  id: string;
  order: number;
  title: string;
  description: string;
  sources: string[];
  typical_depth_m: number | null;
  level: FloodLevel | null;
}

export interface SearchHit {
  label: string;
  lat: number;
  lon: number;
  footprint: Geometry | null;
}

export interface Traveller {
  height_cm: number;
  wading: string;
  mobility_aid: string; // "none" or a key of Options.mobility_aids
  aid_level: number; // index into that device's levels
  preference: string;
  alpha: number | null;
}

export interface TravellerInfo {
  depth_limit_m: number;
  limit_label: string;
  hard_limit_m: number;
  mobility_aid: string;
  alpha: number;
  explanation: string;
}

export interface ChosenPoint extends LatLon {
  label: string | null;
  footprint: Geometry | null;
  source: "map" | "search" | "location";
}

export interface RouteMetrics {
  length_m: number;
  travel_time_s: number;
  max_depth_m: number | null;
  max_depth_label: string;
  wading_length_m: number;
  segments_over_limit: number;
  detour_ratio: number | null;
}

export interface RouteJson {
  geometry: Geometry;
  access_legs: Geometry[];
  uses_steps: boolean;
  max_gradient: number | null; // steepest measured gradient (rise over run); null when none is measured
  min_gradient: number | null; // gentlest measured gradient; null when none is measured
  from: LatLon & { label: string };
  to: LatLon & { label: string | null };
  metrics: RouteMetrics;
}

export interface RouteOption {
  kind: "shortest" | "safe_shortest" | "recommended";
  name: string;
  found: boolean;
  error: string | null;
  route: RouteJson | null;
}

export interface PlaceJson {
  label: string;
  method: "point" | "entrances" | "outline";
  point: LatLon;
  building: Geometry | null;
  access: (LatLon & { label: string })[];
}

export type AlertLevelKey = "ok" | "over_limit" | "deep" | "very_deep" | "critical";

export interface TripPlan {
  start: PlaceJson;
  destination: PlaceJson;
  traveller: {
    depth_limit_m: number;
    limit_label: string;
    height_m: number;
    hard_limit_m: number;
    mobility_aid: string;
    mobility_aid_label: string;
  };
  origin: {
    level: AlertLevelKey;
    level_rank: number;
    depth_m: number | null;
    depth_label: string;
    sheltered: boolean;
    above_knee: boolean;
  };
  has_safe_route: boolean;
  routes: {
    alpha: number;
    blocked_edges: number;
    step_free: boolean; // the traveller cannot use steps or paths steeper than 1:14, so no route uses them
    steps_avoided: boolean; // the plain shortest way has steps these routes avoid
    steep_avoided: boolean; // the plain shortest way has a path steeper than 1:14 these routes avoid
    options: RouteOption[];
  } | null;
  downgrade: {
    body_part: string | null; // a body part for walkers
    aid_level: number | null; // a level of their device for mobility aid users
    label: string;
    body_part_label: string;
    depth_limit_m: number;
    required_depth_m: number;
    route: RouteJson;
  } | null;
  refuge: {
    name: string;
    entrance_label: string;
    within_limit: boolean;
    building: Geometry;
    route: RouteJson;
  } | null;
  least_water: {
    required_depth_m: number | null;
    required_label: string;
    beyond_hard_limit: boolean;
    deepest_point: LatLon;
    route: RouteJson;
  } | null;
  emergency: {
    advice: "available" | "recommended" | "strongly recommended" | "only option";
    // Why: the water where they stand, outside with no refuge, or inside and cut off by deep water.
    reason: "depth" | "no_refuge" | "cut_off";
    sos: LatLon & {
      depth_m: number | null;
      depth_label: string;
      level: AlertLevelKey;
      depth_limit_m: number;
      created_at: string;
    };
  } | null;
}
