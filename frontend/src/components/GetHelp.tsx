import { useEffect, useId, useRef, useState } from "react";
import { useI18n } from "../i18n/I18n";
import type { ChosenPoint } from "../types";
import { type Shared, SosControl, type SosState } from "./Sos";

interface Props {
  start: ChosenPoint | null;
  sos: SosState | null;
  undoSeconds: number;
  onSos: (sos: SosState | null) => void;
}

/** What an SOS sent from here shares: the start stands in for the traveller's position. */
export function sharedLocation(start: ChosenPoint | null): Shared {
  if (!start) return { place: "none" };
  return { place: start.source === "location" ? "current" : "start" };
}

/** Always on the map: calling 000 or VICSES, or alerting people nearby, whatever the trip says. */
export function GetHelp({ start, sos, undoSeconds, onSos }: Props) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      button.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="get-help">
      <button
        ref={button}
        type="button"
        className="get-help-button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
      >
        🆘 {t("help.button")}
      </button>
      {open && (
        <section id={panelId} className="get-help-panel" role="dialog" aria-label={t("help.button")}>
          <div className="get-help-head">
            <h2>{t("help.button")}</h2>
            <button type="button" className="link" onClick={() => setOpen(false)} aria-label={t("help.close")}>
              ✕
            </button>
          </div>
          <a className="button button-danger" href="tel:000">
            📞 {t("help.call000")}
          </a>
          <p className="small">{t("help.lifeDanger")}</p>
          <a className="button" href="tel:132500">
            📞 VICSES 132 500
          </a>
          <p className="small">{t("help.ses")}</p>
          <SosControl sos={sos} shared={sharedLocation(start)} undoSeconds={undoSeconds} onSos={onSos} />
          <p className="small muted">{t("help.simulated")}</p>
        </section>
      )}
    </div>
  );
}
