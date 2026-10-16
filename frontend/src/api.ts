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

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new ApiError("Cannot reach the routing service. Check your connection and try again.");
  }
  if (!response.ok) {
    let message = `The routing service returned an error (${response.status}).`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // keep the generic message
    }
    throw new ApiError(message);
  }
  return response.json() as Promise<T>;
}

function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
}

export const api = {
  area: () => request<Area>("/area"),
  network: () => request<FeatureCollection>("/network"),
  options: () => request<Options>("/options"),
  scenarios: () => request<ScenarioSummary[]>("/scenarios"),
  water: (scenarioId: string) => request<FeatureCollection>(`/scenarios/${encodeURIComponent(scenarioId)}/water`),
  search: (query: string) => request<SearchHit[]>(`/search?q=${encodeURIComponent(query)}`),
  traveller: (t: Traveller, signal?: AbortSignal) => post<TravellerInfo>("/traveller", t, signal),
  trip: (start: ChosenPoint, destination: ChosenPoint, scenarioId: string, t: Traveller, signal?: AbortSignal) =>
    post<TripPlan>(
      "/trip",
      {
        start: { lat: start.lat, lon: start.lon, label: start.label, footprint: start.footprint },
        destination: { lat: destination.lat, lon: destination.lon, label: destination.label, footprint: destination.footprint },
        scenario_id: scenarioId,
        traveller: t,
      },
      signal,
    ),
};
