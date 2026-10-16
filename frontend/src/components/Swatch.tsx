import { ROUTE_STYLES, type RouteKind } from "../routeStyles";

export function Swatch({ colour, dash = "", width = 5 }: { colour: string; dash?: string; width?: number }) {
  return (
    <svg className="swatch" viewBox="0 0 28 10" aria-hidden="true">
      <line x1="2" y1="5" x2="26" y2="5" stroke={colour} strokeWidth={width} strokeDasharray={dash} strokeLinecap="round" />
    </svg>
  );
}

export function RouteSwatch({ kind }: { kind: RouteKind }) {
  const style = ROUTE_STYLES[kind];
  return <Swatch colour={style.colour} dash={style.svgDash} />;
}
