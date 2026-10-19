// The results backend/scripts/benchmark.py writes to docs/benchmark.json (GET /api/benchmark).

export interface Spread {
  median: number | null;
  p95: number | null;
}

export interface Rate {
  count: number;
  of: number;
  rate: number | null;
}

export interface Checks {
  met: number;
  total: number;
  not_met: string[];
}

export interface FaultResult {
  fault: string;
  breaks: string;
  tests_failed: number;
  tests_run: number;
  failed_tests: string[];
  test_town_cases_failed: string[];
  caught: boolean;
}

export interface TravellerSafety {
  with_route: number;
  recommended_over_limit: number;
  shortest_unsafe: number;
  detour_median: number | null;
  detour_p90: number | null;
  over_limit_avoided_m_median: number | null;
  shortest_deepest_median_m: number | null;
  shortest_unknown_depth: number;
  recommended_deepest_median_m: number | null;
  without_route: Record<string, number>;
}

export interface FieldComparison {
  inspected: number;
  paths: {
    inspected: number;
    false_accessible: Rate;
    false_step_free: Rate;
    steps_agree: Rate;
    steps_missed: Rate;
    by_kind: Record<string, { inspected: number; not_passable: Rate; step_free_but_not: Rate }>;
  };
  entrances: { inspected: number; not_usable: Rate; not_step_free: Rate };
}

export interface BenchmarkResults {
  generated_at: string;
  commit: string | null;
  network: { nodes: number; edges: number };
  correctness: {
    dijkstra_node_pairs: {
      pairs: number;
      cost_match: number;
      same_path: number;
      mismatches: string[];
      ours_ms: Spread;
      reference_ms: Spread;
    };
    dijkstra_end_to_end: { routes: number; length_match: number; same_geometry: number; mismatches: string[]; route_ms: Spread };
    minimax_brute_force: { graphs: number; pairs: number; match: number; mismatches: string[] };
    verification: { test_town: Checks; southbank: Checks };
    faults: { baseline: { failed: number; passed: number; skipped: number }; faults: FaultResult[] } | null;
  };
  safety: {
    cost: {
      trips: number;
      levels: Record<string, { title: string; travellers: Record<string, TravellerSafety> }>;
      plan_ms: Record<string, Spread & { plans: number }>;
    };
    rising_flood: {
      trips: number;
      traveller: string;
      schedule: { level: string; from_s: number }[];
      violations_m: number;
      escape_over_limit_m: number;
      reroutes: number;
      trips_rerouted: number;
      caught_by_rising_water: number;
      not_replanned_outside_area: number;
      over_limit_outside_area_m: number;
      outcomes: Record<string, number>;
      extra_walk_median: number | null;
      extra_walk_p90: number | null;
    };
  };
  access: {
    step_free_pairs: {
      pairs: number;
      walking_route: number;
      step_free_route: number;
      step_free_using_steps: number;
      step_free_shorter: number;
      longer_median: number | null;
      longer_p90: number | null;
      longer_max: number | null;
      same_length: number;
    };
  };
  field: FieldComparison | null;
  performance: { plan_ms: Record<string, Spread & { plans: number }>; seconds: Record<string, number> };
}
