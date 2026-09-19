import { HashRouter, Route, Routes } from "react-router-dom";
import TopBar from "./components/Layout/TopBar";
import ChatHome from "./pages/ChatHome";
import MapAnalysis from "./pages/MapAnalysis";
import Dashboard from "./pages/Dashboard";
import Compare from "./pages/Compare";
import Analytics from "./pages/Analytics";
import Knowledge from "./pages/Knowledge";

// HashRouter (not BrowserRouter) → deep links work in every preview/static
// hosting setup without server rewrites. Demo-proof.
export default function App() {
  return (
    <HashRouter>
      <div className="flex h-screen flex-col">
        <TopBar />
        <div className="min-h-0 flex-1">
          <Routes>
            <Route path="/" element={<ChatHome />} />
            <Route path="/map" element={<MapAnalysis />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/knowledge" element={<Knowledge />} />
          </Routes>
        </div>
      </div>
    </HashRouter>
  );
}
