import { getPlaces } from './places';
import { searchLocations } from './locations';

/**
 * Unified search that returns both places and locations
 */
export const searchPlacesAndLocations = async (query = '') => {
  if (!query.trim()) {
    return { data: { items: [] } };
  }

  try {
    // Use wrappers with dev fallbacks (localhost:5050/5000/8000) for reliability.
    const [placesRes, locationsRes] = await Promise.all([
      getPlaces({ q: query }).catch(() => {
        return { data: { items: [] } };
      }),
      searchLocations({ q: query }).catch(() => {
        return { data: { items: [] } };
      }),
    ]);

    const places = (placesRes.data?.items || []).map((p) => ({
      type: 'place',
      ...p,
    }));
    
    const locations = (locationsRes.data?.items || []).map((l) => ({
      type: 'location',
      ...l,
    }));

    const allResults = [...places, ...locations];

    return {
      data: {
        items: allResults,
      },
    };
  } catch {
    return { data: { items: [] } };
  }
};



