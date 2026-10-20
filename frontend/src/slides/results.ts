/* The latest benchmark results on the "How it is tested" slide. They are read from
   docs/benchmark.json (written by backend/scripts/benchmark.py) when the client is built, so they
   are always those /benchmark shows. A result the file does not have is left out. */

import benchmark from "../../../docs/benchmark.json";

export type Result = {
  /** How many, out of how many. */
  value: string;
  of: string;
  label: string;
  /** Why the count is as it should be when it is not all of them. */
  note?: string;
};

const count = (n: number) => n.toLocaleString("en");

export const STEP_FREE_NOTE = "As expected: the other pair includes A\u00a0Block, 256–310 St\u00a0Kilda Road, whose one mapped entrance is reached only by steps.";

/** A number at the path through objects, or undefined if there is none there. */
function numberAt(json: unknown, ...path: string[]): number | undefined {
  let x = json;
  for (const key of path) x = x !== null && typeof x === "object" ? (x as Record<string, unknown>)[key] : undefined;
  return typeof x === "number" && Number.isFinite(x) ? x : undefined;
}

/** The results the slide shows, from benchmark results in the shape of docs/benchmark.json. */
export function readResults(json: unknown): Result[] {
  const results: Result[] = [];
  const share = (met: number | undefined, of: number | undefined, label: string, note?: string) => {
    if (met !== undefined && of !== undefined) results.push({ value: count(met), of: count(of), label, note });
  };
  const sum = (a?: number, b?: number) => (a === undefined || b === undefined ? undefined : a + b);

  const v = ["correctness", "verification"];
  share(
    sum(numberAt(json, ...v, "test_town", "met"), numberAt(json, ...v, "southbank", "met")),
    sum(numberAt(json, ...v, "test_town", "total"), numberAt(json, ...v, "southbank", "total")),
    "hand-derived predictions met, in the test town and Southbank",
  );
  share(
    numberAt(json, "correctness", "dijkstra_node_pairs", "cost_match"),
    numberAt(json, "correctness", "dijkstra_node_pairs", "pairs"),
    "random pairs where the path finder matches NetworkX",
  );
  share(
    numberAt(json, "correctness", "minimax_brute_force", "match"),
    numberAt(json, "correctness", "minimax_brute_force", "pairs"),
    "pairs where the safest path matches brute force",
  );

  const faults = (json as { correctness?: { faults?: { faults?: unknown } | null } } | null)?.correctness?.faults?.faults;
  if (Array.isArray(faults) && faults.length > 0 && faults.every((f) => typeof f?.caught === "boolean")) {
    share(faults.filter((f) => f.caught).length, faults.length, "deliberately broken safety rules caught by the tests");
  }

  const pairs = numberAt(json, "access", "step_free_pairs", "pairs");
  const stepFree = numberAt(json, "access", "step_free_pairs", "step_free_route");
  share(
    stepFree,
    pairs,
    "pairs of buildings with a step-free route between them",
    // The one pair without, found by running the benchmark's pairs again (seed 2026): A Block's
    // only entrance in OpenStreetMap is at the end of a flight of steps, so no step-free route can
    // reach it. A run with another count has not been checked, so it gets no note.
    pairs !== undefined && stepFree === pairs - 1 ? STEP_FREE_NOTE : undefined,
  );
  return results;
}

export const RESULTS = readResults(benchmark);
