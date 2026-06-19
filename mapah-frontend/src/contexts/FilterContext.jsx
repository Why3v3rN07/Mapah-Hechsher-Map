/* eslint-disable react-refresh/only-export-components */
/**
 * FilterContext – shared filter/search state consumed by FilterPanel and MapView.
 */
import { createContext, useContext, useState } from 'react';

const FilterContext = createContext(null);

const DEFAULT_FILTERS = {
  q: '',
  hechshers: [],        // Array of { hechsher_id, hechsher_display_name, hechsher_symbol }
  tags: [],
  radius: 1,
  unit: 'mi',
  lat: null,
  lng: null,
  locationQuery: '',
  locationName: '',     // Display name of selected location
  selectionType: null,  // 'place' | 'location' | null
};

export function FilterProvider({ children }) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const updateFilter = (key, value) =>
    setFilters((prev) => ({ ...prev, [key]: value }));

  const resetFilters = () => setFilters(DEFAULT_FILTERS);

  return (
    <FilterContext.Provider value={{ filters, updateFilter, resetFilters }}>
      {children}
    </FilterContext.Provider>
  );
}

export function useFilters() {
  const ctx = useContext(FilterContext);
  if (!ctx) throw new Error('useFilters must be used inside FilterProvider');
  return ctx;
}


