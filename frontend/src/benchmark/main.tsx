import { createRoot } from "react-dom/client";
import { BenchmarkPage } from "./BenchmarkPage";
import "../theme.css";
import "../docpage.css";

createRoot(document.getElementById("root")!).render(<BenchmarkPage />);
