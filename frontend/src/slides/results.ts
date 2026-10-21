/* The latest benchmark results on the "How it is tested" slide. They are read from
   docs/benchmark.json (written by backend/scripts/benchmark.py) when the client is built, so they
   are always those /benchmark shows. A result the file does not have is left out. */

import benchmark from "../../../docs/benchmark.json";

export type Result = {
  /** How many, out of how many. */
  value: string;
  of: string;
  label: string;
};

const count = (n: number) => n.toLocaleString("en");

/** A number at the path through objects, or undefined if there is none there. */
function numberAt(json: unknown, ...path: string[]): number | undefined {
  let x = json;
  for (const key of path) x = x !== null && typeof x === "object" ? (x as Record<string, unknown>)[key] : undefined;
  return typeof x === "number" && Number.isFinite(x) ? x : undefined;
}

/** The results the slide shows, from benchmark results in the shape of docs/benchmark.json. */
export function readResults(json: unknown): Result[] {
  const results: Result[] = [];
  const share = (met: number | undefined, of: number | undefined, label: string) => {
    if (met !== undefined && of !== undefined) results.push({ value: count(met), of: count(of), label });
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
  return results;
}

export const RESULTS = readResults(benchmark);
