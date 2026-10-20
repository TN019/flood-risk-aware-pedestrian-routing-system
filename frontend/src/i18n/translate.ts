// Filling in a catalogue's sentences. Kept free of React (apart from the node type) so the guidance
// and formatting code can take a translator and be tested with the English one.

import type { ReactNode } from "react";
import { en, type MessageKey, type Messages } from "./messages/en";
import type { Lang } from "./languages";

export type Values = Record<string, string | number>;

/** A sentence of the catalogue, by key, with its {placeholders} filled in. */
export type Translate = (key: MessageKey, values?: Values) => string;

const PLACEHOLDER = /\{(\w+)\}/g;

export function fill(template: string, values: Values = {}): string {
  return template.replace(PLACEHOLDER, (whole, name: string) => (name in values ? String(values[name]) : whole));
}

export function translator(messages: Messages): Translate {
  return (key, values) => fill(messages[key] ?? en[key] ?? key, values);
}

/** English, for tests and for code that runs before a language is chosen. */
export const english: Translate = translator(en);

/** A sentence whose placeholders hold elements (a link, bold text) as well as text. */
export function fillRich(template: string, values: Record<string, ReactNode>): ReactNode[] {
  return template.split(PLACEHOLDER).map((part, i) => (i % 2 === 0 ? part : (values[part] ?? `{${part}}`)));
}

/** Which plural form of a sentence to use for a count ("one" or "other"; the catalogues have only
 * these two, enough for the five languages). */
export function pluralForm(lang: Lang, count: number): "one" | "other" {
  return new Intl.PluralRules(lang).select(count) === "one" ? "one" : "other";
}
