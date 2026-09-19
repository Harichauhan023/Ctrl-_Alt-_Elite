import BusinessSelect from "./BusinessSelect";
import CandidateSites from "./CandidateSites";
import LayersPanel from "./LayersPanel";
import RecommendPanel from "./RecommendPanel";
import WeightsPanel from "./WeightsPanel";

export default function LeftSidebar() {
  return (
    <div className="absolute bottom-3 left-3 top-14 z-10 flex w-72 flex-col gap-2.5 overflow-y-auto pr-0.5">
      <BusinessSelect />
      <RecommendPanel />
      <WeightsPanel />
      <LayersPanel />
      <CandidateSites />
    </div>
  );
}
