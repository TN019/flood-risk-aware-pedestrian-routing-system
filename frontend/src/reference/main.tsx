import { createRoot } from "react-dom/client";
import { I18nProvider, startI18n } from "../i18n/I18n";
import { ReferencePage } from "./ReferencePage";
import "../theme.css";
import "../docpage.css";

startI18n().then((i18n) =>
  createRoot(document.getElementById("root")!).render(
    <I18nProvider initial={i18n}>
      <ReferencePage />
    </I18nProvider>,
  ),
);
