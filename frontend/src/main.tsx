import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

// No <StrictMode>: in development it mounts every component twice, which creates and throws away an
// extra WebGL map each time. Safari has few WebGL contexts to spare and starts losing them.
createRoot(document.getElementById("root")!).render(<App />);
