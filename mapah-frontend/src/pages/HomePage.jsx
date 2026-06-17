import FilterPanel from '../components/Filters/FilterPanel';
import MapView from '../components/Map/MapView';

export default function HomePage({ openGlobalSubmission }) {
  return (
    <div className="layout-shell">
      <FilterPanel />
      <MapView
        onTagPlace={(place) => openGlobalSubmission('tag_update', place)}
        onEditPlace={(place) => openGlobalSubmission('edit', place)}
      />
    </div>
  );
}



