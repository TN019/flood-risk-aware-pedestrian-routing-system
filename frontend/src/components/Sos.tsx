import { useEffect, useState } from "react";
import { useI18n } from "../i18n/I18n";
import type { Translate } from "../i18n/translate";

/** What an SOS shares: the traveller's current location, their start point standing in for it,
 * nothing, or where the trip plan says they stand (with the water depth there, e.g. "52 cm"). */
export type Shared = { place: "none" | "current" | "start" } | { place: "here"; depth: string | null };

/** An SOS alert sent to people nearby (simulated): when, and what it shared. */
export interface SosState {
  sentAt: number;
  shared: Shared;
}

/** What an SOS shares, in words, e.g. "your location and 52 cm water depth". */
export function sharedText(shared: Shared, t: Translate): string {
  switch (shared.place) {
    case "none":
      return t("sos.noLocation");
    case "current":
      return t("sos.currentLocation");
    case "start":
      return t("sos.startAsLocation");
    default:
      return shared.depth === null ? t("sos.here") : t("sos.hereWithDepth", { depth: shared.depth });
  }
}

interface Props {
  sos: SosState | null;
  shared: Shared;
  undoSeconds: number;
  onSos: (sos: SosState | null) => void;
}

/** The SOS button, or once sent, when it was sent with an undo for the first few seconds. */
export function SosControl({ sos, shared, undoSeconds, onSos }: Props) {
  const { t } = useI18n();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (sos === null) return;
    const timer = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(timer);
  }, [sos]);

  if (sos === null) {
    return (
      <button type="button" className="button" onClick={() => onSos({ sentAt: Date.now(), shared })}>
        📣 {t("sos.button")}
      </button>
    );
  }
  const elapsed = Math.max(0, (now - sos.sentAt) / 1000);
  return (
    <div className="sos-sent" role="status">
      <span>{t("sos.sent", { seconds: Math.round(elapsed), shared: sharedText(sos.shared, t) })}</span>
      {elapsed < undoSeconds && (
        <button type="button" className="link" onClick={() => onSos(null)}>
          {t("sos.undo", { seconds: Math.ceil(undoSeconds - elapsed) })}
        </button>
      )}
    </div>
  );
}
