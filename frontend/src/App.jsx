import { Route, Routes } from "react-router-dom";

import DashboardLayout from "./layouts/DashboardLayout.jsx";
import AboutDataset from "./pages/AboutDataset.jsx";
import DataExplorer from "./pages/DataExplorer.jsx";
import GraphAnalytics from "./pages/GraphAnalytics.jsx";
import MachineLearning from "./pages/MachineLearning.jsx";
import MapExplorer from "./pages/MapExplorer.jsx";
import NotFound from "./pages/NotFound.jsx";
import Overview from "./pages/Overview.jsx";
import RegionalComparison from "./pages/RegionalComparison.jsx";
import RoadInfrastructure from "./pages/RoadInfrastructure.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/map-explorer" element={<MapExplorer />} />
        <Route path="/road-infrastructure" element={<RoadInfrastructure />} />
        <Route path="/regional-comparison" element={<RegionalComparison />} />
        <Route path="/machine-learning" element={<MachineLearning />} />
        <Route path="/graph-analytics" element={<GraphAnalytics />} />
        <Route path="/data-explorer" element={<DataExplorer />} />
        <Route path="/about-dataset" element={<AboutDataset />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
