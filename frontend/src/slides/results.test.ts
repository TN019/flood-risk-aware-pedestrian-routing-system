import { describe, expect, it } from "vitest";
import benchmark from "../../../docs/benchmark.json";
import { readResults, STEP_FREE_NOTE } from "./results";

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
      ["299", "300"],
    ]);
  });

  it("leaves out what the results do not have", () => {
    const partial = {
      correctness: { ...FULL.correctness, verification: { test_town: FULL.correctness.verification.test_town }, faults: null },
      access: FULL.access,
    };
    expect(readResults(partial).map((r) => r.value)).toEqual(["1,000", "890", "299"]);
    expect(readResults({})).toEqual([]);
    expect(readResults(null)).toEqual([]);
  });

  it("explains the one pair without a step-free route, and no other count", () => {
    const stepFree = (pairs: number, route: number) =>
      readResults({ access: { step_free_pairs: { pairs, step_free_route: route } } })[0].note;
    expect(stepFree(300, 299)).toBe(STEP_FREE_NOTE);
    expect(stepFree(300, 300)).toBeUndefined();
    expect(stepFree(300, 298)).toBeUndefined();
  });

  it("reads docs/benchmark.json", () => {
    const results = readResults(benchmark);
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) expect(`${r.value} of ${r.of}`, r.label).toMatch(/^[\d,]+ of [\d,]+$/);
  });
});
