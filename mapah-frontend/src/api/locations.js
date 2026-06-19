import client from './client';
import axios from 'axios';

const MAPBOX_PUBLIC_GEOCODE_BASE = 'https://api.mapbox.com/geocoding/v5/mapbox.places';

async function searchLocationsViaMapbox(params = {}) {
  const token = import.meta.env.VITE_MAPBOX_TOKEN;
  const q = String(params.q ?? '').trim();
  if (!token || !q) return null;

  const limit = Number.isFinite(Number(params.limit)) ? Number(params.limit) : 8;
  const encoded = encodeURIComponent(q);
  const { data } = await axios.get(`${MAPBOX_PUBLIC_GEOCODE_BASE}/${encoded}.json`, {
    params: {
      access_token: token,
      autocomplete: true,
      limit,
    },
  });

  const items = (data?.features || []).map((feature) => {
    const [lng, lat] = feature?.geometry?.coordinates || [];
    return {
      place_name: feature?.place_name || '',
      lat: Number(lat),
      lng: Number(lng),
    };
  }).filter((item) => Number.isFinite(item.lat) && Number.isFinite(item.lng));

  return { data: { items } };
}

/**
 * @param {Object} params – q (query string)
 */
export const searchLocations = async (params = {}) => {
  try {
    // Fast path: query Mapbox directly from the browser when a public token exists.
    const mapboxRes = await searchLocationsViaMapbox(params);
    if (mapboxRes) return mapboxRes;

    return await client.get('/api/locations/search', { params });
  } catch (error) {
    // Fallbacks for local dev when proxy is not configured/running.
    const status = error?.response?.status;
    const shouldTryFallback = !status || status === 404 || status >= 500;
    if (!shouldTryFallback) throw error;

    const fallbackBases = ['http://localhost:5050', 'http://localhost:5000', 'http://localhost:8000'];
    for (const baseURL of fallbackBases) {
      try {
        return await axios.get(`${baseURL}/api/locations/search`, {
          params,
          withCredentials: true,
        });
      } catch (fallbackError) {
        const fallbackStatus = fallbackError?.response?.status;
        const shouldContinue = !fallbackStatus || fallbackStatus === 404 || fallbackStatus >= 500;
        if (!shouldContinue) throw fallbackError;
      }
    }

    // Last-resort fallback: query Mapbox directly with the public frontend token.
    const mapboxFallback = await searchLocationsViaMapbox(params);
    if (mapboxFallback) return mapboxFallback;

    throw error;
  }
};

export const reverseGeocode = async (lat, lng) => {
  const token = import.meta.env.VITE_MAPBOX_TOKEN;
  if (!token || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lng))) {
    return null;
  }

  const { data } = await axios.get(`${MAPBOX_PUBLIC_GEOCODE_BASE}/${Number(lng)},${Number(lat)}.json`, {
    params: {
      access_token: token,
      limit: 1,
    },
  });

  const placeName = data?.features?.[0]?.place_name;
  return placeName || null;
};

