import { describe, expect, it } from "vitest";
import benchmark from "../../../docs/benchmark.json";
import { readResults } from "./results";

const FULL = {
  correctness: {
    dijkstra_node_pairs: { pairs: 1000, cost_match: 1000 },
    minimax_brute_force: { pairs: 891, match: 890 },
    verification: { test_town: { met: 130, total: 130 }, southbank: { met: 38, total: 39 } },
    faults: { faults: [{ caught: true }, { caught: false }, { caught: true }] },
  },
  safety: { rising_flood: { violations_m: 12.6 } },
  access: { step_free_pairs: { pairs: 300, step_free_route: 299 } },
};

describe("readResults", () => {
  it("reads each result, in order", () => {
    expect(readResults(FULL).map((r) => [r.value, r.of])).toEqual([
      ["168", "169"],
      ["1,000", "1,000"],
      ["890", "891"],
      ["2", "3"],
    ]);
  });

  it("leaves out what the results do not have", () => {
    const partial = {
      correctness: { ...FULL.correctness, verification: { test_town: FULL.correctness.verification.test_town }, faults: null },
    };
    expect(readResults(partial).map((r) => r.value)).toEqual(["1,000", "890"]);
    expect(readResults({})).toEqual([]);
    expect(readResults(null)).toEqual([]);
  });

  it("reads docs/benchmark.json", () => {
    const results = readResults(benchmark);
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) expect(`${r.value} of ${r.of}`, r.label).toMatch(/^[\d,]+ of [\d,]+$/);
  });
});
