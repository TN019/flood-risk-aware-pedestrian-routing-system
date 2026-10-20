import { createRoot } from "react-dom/client";
import App from "./App";
import { I18nProvider, startI18n } from "./i18n/I18n";
import "./styles.css";

// No <StrictMode>: in development it mounts every component twice, which creates and throws away an
// extra WebGL map each time. Safari has few WebGL contexts to spare and starts losing them.
startI18n().then((i18n) =>
  createRoot(document.getElementById("root")!).render(
    <I18nProvider initial={i18n}>
      <App />
    </I18nProvider>,
  ),
);
