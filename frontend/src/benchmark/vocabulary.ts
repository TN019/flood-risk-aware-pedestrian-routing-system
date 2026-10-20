import type { MessageKey } from "../i18n/messages/en";
import type { Translate } from "../i18n/translate";

// docs/benchmark.json names its travellers, outcomes and faults in English; these are their words in
// the catalogues. Anything new is shown as written until it is added here.
export const TRAVELLERS: Record<string, MessageKey> = {
  "adult, ankle": "bench.traveller.adultAnkle",
  "adult, mid calf": "bench.traveller.adultMidCalf",
  "child, mid calf": "bench.traveller.childMidCalf",
  "manual wheelchair, 5 cm": "bench.traveller.manualWheelchair5",
};
export const OUTCOMES: Record<string, MessageKey> = {
  arrived: "bench.outcome.arrived",
  "at a shelter": "bench.outcome.atShelter",
  "higher limit": "bench.outcome.higherLimit",
  shelter: "bench.outcome.shelter",
  "stay inside": "bench.outcome.stayInside",
  "emergency help": "bench.outcome.emergencyHelp",
  "not connected": "bench.outcome.notConnected",
  nothing: "bench.outcome.nothing",
};

export function words(t: Translate, keys: Record<string, MessageKey>, english: string): string {
  return english in keys ? t(keys[english]) : english;
}

export function faultText(t: Translate, fault: string, english: string): string {
  const key = `bench.fault.${fault}` as MessageKey;
  return t(key) === key ? english : t(key);
}
