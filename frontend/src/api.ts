import type {
  Area,
  ChosenPoint,
  FeatureCollection,
  Options,
  ScenarioSummary,
  SearchHit,
  Traveller,
  TravellerInfo,
  TripPlan,
} from "./types";
import type { BenchmarkResults } from "./benchmark/types";
import type { Lang } from "./i18n/languages";
import type { Translate } from "./i18n/translate";

/** A request that failed: with the API's own message (already in the language asked for), or
 * because the API could not be reached or answered with an error and no message. */
export class ApiError extends Error {
  constructor(
    readonly detail: string | null,
    readonly status: number | null = null,
  ) {
    super(detail ?? `request failed (${status ?? "unreachable"})`);
  }

  text(t: Translate): string {
    if (this.detail) return this.detail;
    return this.status === null ? t("error.unreachable") : t("error.status", { status: this.status });
  }
}

/** What to tell the traveller about a failed request. */
export function errorText(err: unknown, t: Translate, fallback: string): string {
  return err instanceof ApiError ? err.text(t) : fallback;
}

async function request<T>(path: string, lang: Lang, init?: RequestInit): Promise<T> {
  let response: Response;
  const url = `/api${path}${path.includes("?") ? "&" : "?"}lang=${encodeURIComponent(lang)}`;
  try {
    response = await fetch(url, init);
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError(null);
  }
  if (!response.ok) {
    let detail: string | null = null;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // no message of its own
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

function post<T>(path: string, lang: Lang, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, lang, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

// Every call names the language its text should come in.
export const api = {
  area: (lang: Lang) => request<Area>("/area", lang),
  network: (lang: Lang) => request<FeatureCollection>("/network", lang),
  options: (lang: Lang) => request<Options>("/options", lang),
  benchmark: (lang: Lang) => request<BenchmarkResults>("/benchmark", lang),
  scenarios: (lang: Lang) => request<ScenarioSummary[]>("/scenarios", lang),
  water: (scenarioId: string, lang: Lang) => request<FeatureCollection>(`/scenarios/${encodeURIComponent(scenarioId)}/water`, lang),
  search: (query: string, lang: Lang) => request<SearchHit[]>(`/search?q=${encodeURIComponent(query)}`, lang),
  traveller: (t: Traveller, lang: Lang, signal?: AbortSignal) => post<TravellerInfo>("/traveller", lang, t, signal),
  trip: (start: ChosenPoint, destination: ChosenPoint, scenarioId: string, t: Traveller, lang: Lang, signal?: AbortSignal) =>
    post<TripPlan>(
      "/trip",
      lang,
      {
        start: { lat: start.lat, lon: start.lon, label: start.label, footprint: start.footprint },
        destination: { lat: destination.lat, lon: destination.lon, label: destination.label, footprint: destination.footprint },
        scenario_id: scenarioId,
        traveller: t,
      },
      signal,
    ),
};
