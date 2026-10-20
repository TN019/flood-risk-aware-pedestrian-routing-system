import { describe, expect, it } from "vitest";
import benchmark from "../../../docs/benchmark.json";
import { faultText, OUTCOMES, TRAVELLERS } from "../benchmark/vocabulary";
import type { BenchmarkResults } from "../benchmark/types";
import { chooseLang, LANGUAGES, offered } from "./languages";
import { en } from "./messages/en";
import es from "./messages/es";
import hi from "./messages/hi";
import ko from "./messages/ko";
import zhHans from "./messages/zh-Hans";
import { english, fill, fillRich, pluralForm } from "./translate";

const CATALOGUES = { es, "zh-Hans": zhHans, hi, ko };

const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();
// Every number, e.g. "0.59", "1:14", "22,631"; digits in another script would not match, so each
// language must write them as in English.
const numbers = (text: string) => new Set(text.match(/\d+(?:[.,:]\d+)*/g) ?? []);
// The translation has every number of the English and no other; the "1" of "1-in-100-year" may be
// left out, as in "100-year".
function missingOrExtra(translation: string, english: string): string[] {
  const has = numbers(translation);
  const all = numbers(english);
  const required = numbers(english.replace(/\b1-in-(?=\d)/g, ""));
  return [...[...required].filter((n) => !has.has(n)), ...[...has].filter((n) => !all.has(n))];
}

describe("catalogues", () => {
  it("cover every offered language", () => {
    expect(Object.keys(CATALOGUES).sort()).toEqual(LANGUAGES.map((l) => l.code).filter((c) => c !== "en").sort());
  });

  for (const [lang, messages] of Object.entries(CATALOGUES)) {
    it(`${lang} has every sentence, none empty`, () => {
      expect(Object.keys(messages).sort()).toEqual(Object.keys(en).sort());
      for (const [key, text] of Object.entries(messages)) expect(text.trim(), key).not.toBe("");
    });

    it(`${lang} keeps every placeholder and number`, () => {
      for (const [key, source] of Object.entries(en)) {
        const text = messages[key as keyof typeof en];
        expect(placeholders(text), key).toEqual(placeholders(source));
        expect(missingOrExtra(text, source), key).toEqual([]);
      }
    });
  }
});

describe("choosing the language", () => {
  it("reads BCP 47 tags", () => {
    expect(offered("es-AR")).toBe("es");
    expect(offered("zh-CN")).toBe("zh-Hans");
    expect(offered("zh-TW")).toBe("zh-Hans");
    expect(offered("zh-Hans")).toBe("zh-Hans");
    expect(offered("hi_IN")).toBe("hi");
    expect(offered("KO")).toBe("ko");
    expect(offered("fr")).toBeNull();
    expect(offered(null)).toBeNull();
  });

  it("keeps the earlier choice, else follows the browser, else English", () => {
    expect(chooseLang("ko", ["es-ES", "en"])).toBe("ko");
    expect(chooseLang(null, ["fr-FR", "es-MX", "en"])).toBe("es");
    expect(chooseLang("nonsense", ["de"])).toBe("en");
    expect(chooseLang(null, [])).toBe("en");
  });
});

describe("filling in sentences", () => {
  it("puts values into placeholders and leaves unknown ones", () => {
    expect(fill("{a} of {b}", { a: 3, b: "ten" })).toBe("3 of ten");
    expect(fill("{a} {missing}", { a: 1 })).toBe("1 {missing}");
    expect(english("unit.min", { count: 4 })).toBe("4 min");
  });

  it("puts elements into placeholders", () => {
    const strong = { type: "strong" } as unknown as React.ReactNode;
    expect(fillRich("Your limit: {limit}.", { limit: strong })).toEqual(["Your limit: ", strong, "."]);
  });

  it("picks the plural form by each language's rules", () => {
    expect(pluralForm("en", 1)).toBe("one");
    expect(pluralForm("en", 2)).toBe("other");
    expect(pluralForm("es", 1)).toBe("one");
    expect(pluralForm("ko", 1)).toBe("other");
    expect(pluralForm("zh-Hans", 1)).toBe("other");
  });
});

describe("the benchmark record", () => {
  it("has words for every traveller, outcome and fault it names", () => {
    const r = benchmark as unknown as BenchmarkResults;
    const levels = Object.values(r.safety.cost.levels);
    const travellers = [...levels.flatMap((l) => Object.keys(l.travellers)), r.safety.rising_flood.traveller];
    const outcomes = [
      ...levels.flatMap((l) => Object.values(l.travellers).flatMap((t) => Object.keys(t.without_route))),
      ...Object.keys(r.safety.rising_flood.outcomes),
    ];
    for (const name of travellers) expect(TRAVELLERS, name).toHaveProperty([name]);
    for (const name of outcomes) expect(OUTCOMES, name).toHaveProperty([name]);
    for (const f of r.correctness.faults?.faults ?? []) {
      expect(en, f.fault).toHaveProperty([`bench.fault.${f.fault}`]);
      expect(faultText(english, f.fault, "")).toBe(f.breaks);
    }
  });
});
