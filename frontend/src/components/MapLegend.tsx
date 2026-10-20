import { route } from "../guidance";
import { useI18n } from "../i18n/I18n";
import { DRAW_ORDER, type RouteKind } from "../routeStyles";
import type { TripPlan } from "../types";
import { COLOURS } from "./MapView";
import { RouteSwatch, Swatch } from "./Swatch";

interface Props {
  trip: TripPlan | null;
  selected: RouteKind | null;
  hasWater: boolean;
}

/** Only what is on the map now: the water, each route drawn, and the deepest point if marked. */
export function MapLegend({ trip, selected, hasWater }: Props) {
  const { t } = useI18n();
  const kinds = trip ? [...DRAW_ORDER].reverse().filter((k) => route(trip, k)) : [];
  // Routes that follow the same line are drawn once, as the most important of them.
  const shown = kinds.filter((k, i) => !kinds.slice(0, i).some((j) => JSON.stringify(route(trip!, j)!.geometry) === JSON.stringify(route(trip!, k)!.geometry)));
  const name = (k: RouteKind) => {
    if (k === "downgrade" && trip?.downgrade) {
      const d = trip.downgrade;
      return d.body_part !== null
        ? t("legend.downgradeBody", { label: d.label })
        : t("legend.downgradeAid", { depth: `${Math.round(d.depth_limit_m * 1000) / 10} cm` });
    }
    if (k === "shortest" && route(trip!, k)!.metrics.segments_over_limit > 0) return t("legend.shortestUnsafe");
    return t(`route.${k}`);
  };
  if (!hasWater && shown.length === 0) return null;
  // On a phone the map is small: the legend starts folded.
  const phone = typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches;
  return (
    <details className="map-legend" open={!phone}>
      <summary>{t("legend.title")}</summary>
      <div className="legend-items">
      {hasWater && (
        <>
          <span>
            <Swatch colour={COLOURS.water} width={4} /> {t("legend.waterOk")}
          </span>
          <span>
            <Swatch colour={COLOURS.overLimit} dash="5 3" width={4} /> {t("legend.waterOver")}
          </span>
        </>
      )}
      {shown.map((k) => (
        <span key={k} className={selected === k ? "legend-on" : ""}>
          <RouteSwatch kind={k} /> {name(k)}
        </span>
      ))}
      {trip?.least_water && (
        <span>
          <i className="legend-dot" /> {t("legend.deepest")}
        </span>
      )}
      </div>
    </details>
  );
}
