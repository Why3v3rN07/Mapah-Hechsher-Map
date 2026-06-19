import { useFilters } from '../../contexts/FilterContext';
import HechsherSearch from './HechsherSearch';
import UnifiedSearch from './UnifiedSearch';
import './FilterPanel.css';

const ALL_TAGS = ['restaurant', 'bakery', 'store', 'cafe', 'meat', 'dairy', 'parve'];

export default function FilterPanel() {
  const { filters, updateFilter, resetFilters } = useFilters();

  const handleTagToggle = (tag) => {
    const next = filters.tags.includes(tag)
      ? filters.tags.filter((t) => t !== tag)
      : [...filters.tags, tag];
    updateFilter('tags', next);
  };

  return (
    <aside className="filter-panel">
      {/* Unified search for places and locations */}
      <div className="filter-section">
        <label className="filter-label">Search</label>
         <UnifiedSearch
           valuePlaceName={filters.q}
           valueLocationName={filters.locationQuery}
           onSelectPlace={(q, lat, lng) => {
             updateFilter('q', q);
             updateFilter('selectionType', 'place');
             // Clear location filter when selecting a place
             updateFilter('locationQuery', '');
             if (Number.isFinite(lat) && Number.isFinite(lng)) {
               updateFilter('lat', lat);
               updateFilter('lng', lng);
             } else {
               updateFilter('lat', null);
               updateFilter('lng', null);
             }
           }}
           onSelectLocation={(locationName, lat, lng) => {
             updateFilter('selectionType', 'location');
             // Clear place filter when selecting a location
             updateFilter('q', '');
             updateFilter('locationQuery', locationName);
             if (Number.isFinite(lat) && Number.isFinite(lng)) {
               updateFilter('lat', lat);
               updateFilter('lng', lng);
             } else {
               updateFilter('lat', null);
               updateFilter('lng', null);
             }
           }}
          onClear={() => {
            updateFilter('q', '');
            updateFilter('locationQuery', '');
            updateFilter('lat', null);
            updateFilter('lng', null);
          }}
        />
      </div>

      {/* Hechsher typeahead */}
      <div className="filter-section">
        <label className="filter-label">Hechsher</label>
        <HechsherSearch
          value={filters.hechshers}
          onChange={(hs) => updateFilter('hechshers', hs)}
        />
      </div>

      {/* Tags */}
      <div className="filter-section">
        <label className="filter-label">Tags</label>
        <div className="tag-grid">
          {ALL_TAGS.map((tag) => (
            <button
              key={tag}
              className={`tag-btn ${filters.tags.includes(tag) ? 'tag-btn--active' : ''}`}
              onClick={() => handleTagToggle(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

       <button className="btn btn-ghost filter-reset" onClick={resetFilters}>
         Reset filters
       </button>
     </aside>
   );
}

