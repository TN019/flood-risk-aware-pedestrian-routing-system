import { useEffect, useState } from "react";

/** An SOS alert sent to people nearby (simulated): when, and what it shared. */
export interface SosState {
  sentAt: number;
  shared: string; // e.g. "your location and 52 cm water depth"
}

interface Props {
  sos: SosState | null;
  shared: string;
  undoSeconds: number;
  onSos: (sos: SosState | null) => void;
}

/** The SOS button, or once sent, when it was sent with an undo for the first few seconds. */
export function SosControl({ sos, shared, undoSeconds, onSos }: Props) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (sos === null) return;
    const timer = window.setInterval(() => setNow(Date.now()), 500);
    return () => window.clearInterval(timer);
  }, [sos]);

  if (sos === null) {
    return (
      <button type="button" className="button" onClick={() => onSos({ sentAt: Date.now(), shared })}>
        📣 Alert people nearby (SOS)
      </button>
    );
  }
  const elapsed = Math.max(0, (now - sos.sentAt) / 1000);
  return (
    <div className="sos-sent" role="status">
      <span>
        SOS sent {Math.round(elapsed)} s ago with {sos.shared} (simulated).
      </span>
      {elapsed < undoSeconds && (
        <button type="button" className="link" onClick={() => onSos(null)}>
          Undo ({Math.ceil(undoSeconds - elapsed)} s)
        </button>
      )}
    </div>
  );
}
