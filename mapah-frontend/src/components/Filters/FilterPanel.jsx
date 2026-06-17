import { useFilters } from '../../contexts/FilterContext';
import HechsherSearch from './HechsherSearch';
import UnifiedSearch from './UnifiedSearch';
import './FilterPanel.css';

const ALL_TAGS = ['restaurant', 'bakery', 'store', 'cafe', 'meat', 'dairy', 'parve'];
const MAX_RADIUS_MI = 10;
const MAX_RADIUS_KM = 16.09;

export default function FilterPanel() {
  const { filters, updateFilter, resetFilters } = useFilters();

  const handleTagToggle = (tag) => {
    const next = filters.tags.includes(tag)
      ? filters.tags.filter((t) => t !== tag)
      : [...filters.tags, tag];
    updateFilter('tags', next);
  };

  const maxRadius = filters.unit === 'mi' ? MAX_RADIUS_MI : MAX_RADIUS_KM;

  return (
    <aside className="filter-panel">
      {/* Unified search for places and locations */}
      <div className="filter-section">
        <label className="filter-label">Search</label>
        <UnifiedSearch
          valuePlaceName={filters.q}
          valueLocationName={filters.locationQuery}
          onSelectPlace={(q) => {
            updateFilter('q', q);
            // Clear location filter when selecting a place
            updateFilter('locationQuery', '');
            updateFilter('lat', null);
            updateFilter('lng', null);
          }}
          onSelectLocation={(locationName, lat, lng) => {
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
          value={filters.hechsher}
          onChange={(h) => updateFilter('hechsher', h)}
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

       {/* Proximity */}
       <div className="filter-section">
         <label className="filter-label">
           Radius: <strong>{filters.radius} {filters.unit}</strong>
         </label>
         <input
           type="range"
           min={0.1}
           max={maxRadius}
           step={0.1}
           value={filters.radius}
           onChange={(e) => updateFilter('radius', parseFloat(e.target.value))}
           className="range-input"
         />
         <div className="unit-switch">
           {['mi', 'km'].map((u) => (
             <button
               key={u}
               className={`unit-btn ${filters.unit === u ? 'unit-btn--active' : ''}`}
               onClick={() => updateFilter('unit', u)}
             >
               {u}
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

