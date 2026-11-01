import { NavLink, Route, Routes } from "react-router-dom";
import { KpiPage } from "./pages/KpiPage";
import { LeadPage } from "./pages/LeadPage";
import { QueuePage } from "./pages/QueuePage";
import { VisibilityPage } from "./pages/VisibilityPage";

export function App() {
  return (
    <div className="wrap">
      <header>
        <p className="brand">LeadRoute</p>
        <p className="tagline">Code decides. The model only proposes evidence.</p>
      </header>
      <nav>
        <NavLink to="/" end>
          Queue
        </NavLink>
        <NavLink to="/kpi">KPI pack</NavLink>
        <NavLink to="/visibility">AI visibility</NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<QueuePage />} />
        <Route path="/leads/:personId" element={<LeadPage />} />
        <Route path="/kpi" element={<KpiPage />} />
        <Route path="/visibility" element={<VisibilityPage />} />
      </Routes>
    </div>
  );
}
