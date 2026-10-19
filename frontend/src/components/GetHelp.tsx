import { useEffect, useId, useRef, useState } from "react";
import type { ChosenPoint } from "../types";
import { SosControl, type SosState } from "./Sos";

interface Props {
  start: ChosenPoint | null;
  sos: SosState | null;
  undoSeconds: number;
  onSos: (sos: SosState | null) => void;
}

/** What an SOS sent from here shares: the start stands in for the traveller's position. */
export function sharedLocation(start: ChosenPoint | null): string {
  if (!start) return "no location (set a start to share one)";
  return start.source === "location" ? "your current location" : "your start point as your location";
}

/** Always on the map: calling 000 or VICSES, or alerting people nearby, whatever the trip says. */
export function GetHelp({ start, sos, undoSeconds, onSos }: Props) {
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
        🆘 Get help
      </button>
      {open && (
        <section id={panelId} className="get-help-panel" role="dialog" aria-label="Get help">
          <div className="get-help-head">
            <h2>Get help</h2>
            <button type="button" className="link" onClick={() => setOpen(false)} aria-label="Close">
              ✕
            </button>
          </div>
          <a className="button button-danger" href="tel:000">
            📞 Call 000
          </a>
          <p className="small">If anyone's life is in danger.</p>
          <a className="button" href="tel:132500">
            📞 VICSES 132 500
          </a>
          <p className="small">Flood or storm help: trapped by water, water coming inside, a fallen tree.</p>
          <SosControl sos={sos} shared={sharedLocation(start)} undoSeconds={undoSeconds} onSos={onSos} />
          <p className="small muted">Calls open your phone's dialler. The SOS alert is simulated in this version.</p>
        </section>
      )}
    </div>
  );
}
