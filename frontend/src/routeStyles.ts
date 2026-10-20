// How each kind of route is drawn, shared by the map, the legend and the panel. Each is named in the
// catalogue as route.<kind>.

export type RouteKind = "recommended" | "safe_shortest" | "shortest" | "downgrade" | "refuge" | "least_water";

export interface RouteStyle {
  colour: string;
  map: { width: number; dash?: [number, number] }; // MapLibre line-dasharray, in line widths
  svgDash: string; // the same pattern for the small swatches
}

export const ROUTE_STYLES: Record<RouteKind, RouteStyle> = {
  recommended: { colour: "#7b2cbf", map: { width: 7 }, svgDash: "" },
  safe_shortest: { colour: "#e6550d", map: { width: 5, dash: [0.1, 1.6] }, svgDash: "1 5" },
  shortest: { colour: "#555555", map: { width: 4, dash: [2, 1.5] }, svgDash: "6 4" },
  downgrade: { colour: "#b07cd8", map: { width: 5, dash: [2, 1.2] }, svgDash: "6 4" },
  refuge: { colour: "#2ca02c", map: { width: 6 }, svgDash: "" },
  least_water: { colour: "#8c510a", map: { width: 5, dash: [1.5, 1] }, svgDash: "5 3" },
};

// Drawn from bottom to top; a selected route is also drawn again above all of them.
export const DRAW_ORDER: RouteKind[] = ["least_water", "refuge", "shortest", "safe_shortest", "downgrade", "recommended"];
