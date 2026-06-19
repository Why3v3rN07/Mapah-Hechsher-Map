/**
 * MapView – Mapbox map that re-fetches places whenever filters change.
 *
 * Clicking a marker opens a popup with place details, a Tag action (all users),
 * and an Edit action (authenticated users only).
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { useAuth } from '../../contexts/AuthContext';
import { useFilters } from '../../contexts/FilterContext';
import { getPlaces } from '../../api/places';
import './MapView.css';

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;

const FALLBACK_CENTER = [35.2137, 31.7683]; // Israel

export default function MapView({ onTagPlace, onEditPlace }) {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const { filters } = useFilters();
  const { user } = useAuth();
  const [mapReady, setMapReady] = useState(false);

  // ── Init map ────────────────────────────────────────────────────────
  useEffect(() => {
    if (mapRef.current) return;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: FALLBACK_CENTER,
      zoom: 7,
    });

    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.addControl(
      new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: false,
        showUserHeading: false,
      }),
      'top-right',
    );

    map.on('load', () => {
      setMapReady(true);

      // Centre on user location if available
      navigator.geolocation?.getCurrentPosition(
        ({ coords }) => map.setCenter([coords.longitude, coords.latitude]),
        () => { /* use fallback */ },
        { timeout: 5000 },
      );

      // Click on empty map → centre + gentle zoom in
      map.on('click', (e) => {
        // Ignore clicks that land on a marker/popup layer
        const features = map.queryRenderedFeatures(e.point);
        const hitInteractable = features.some(
          (f) => f.layer && (f.layer.type === 'symbol' || f.layer.type === 'circle'),
        );
        if (hitInteractable) return;

        map.easeTo({
          center: e.lngLat,
          zoom: Math.min(map.getZoom() + 1.5, 18),
          duration: 400,
        });
      });
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Fly to selected location when user picks from search dropdown ────────
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    if (filters.lat == null || filters.lng == null) return;

    // Use different zoom levels for places vs generic locations
    const zoom = filters.selectionType === 'place' ? 16 : 14;

    // Fly to the selected location with zoom matching selection type
    mapRef.current.easeTo({
      center: [filters.lng, filters.lat],
      zoom,
      duration: 600,
    });
  }, [mapReady, filters.lat, filters.lng, filters.selectionType]);

  // ── Fetch + render markers whenever filters change ────────────────────
  const renderMarkers = useCallback(
    async (places) => {
      if (!mapRef.current) return;

      // Remove old markers
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];

      places.forEach((place) => {
        if (place.latitude == null || place.longitude == null) return;
        const lat = Number(place.latitude);
        const lng = Number(place.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

        // Build popup HTML
        const hechsherList = (place.hechshers || [])
          .map((h) =>
            h.hechsher_symbol
              ? `<img src="${h.hechsher_symbol}" alt="${h.hechsher_display_name}" class="popup-hechsher-icon" title="${h.hechsher_display_name}" />`
              : `<span class="popup-hechsher-name">${h.hechsher_display_name}</span>`,
          )
          .join('');

        const tagList = (place.tags || []).map((t) => `<span class="popup-tag">${t}</span>`).join('');
        const dist = place.distance
          ? `<span class="popup-distance">${place.distance.value} ${place.distance.unit}</span>`
          : '';
        const editBtn = user
          ? `<button class="popup-action-btn" data-action="edit" data-id="${place.place_id}">✏️ Edit</button>`
          : '';

        const popupHtml = `
          <div class="popup-content">
            <strong class="popup-name">${place.place_name}</strong>
            ${dist}
            <div class="popup-address">${place.street_address ?? ''}</div>
            <div class="popup-hechshers">${hechsherList}</div>
            <div class="popup-tags">${tagList}</div>
            <div class="popup-actions">
              <button class="popup-action-btn" data-action="tag" data-id="${place.place_id}">🏷️ Tag</button>
              ${editBtn}
            </div>
          </div>`;

        const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(popupHtml);

        popup.on('open', () => {
          // Delegate clicks to popup buttons
          const popupEl = popup.getElement();
          popupEl?.querySelectorAll('[data-action]').forEach((btn) => {
            btn.onclick = () => {
              const action = btn.dataset.action;
              if (action === 'tag') onTagPlace?.(place);
              if (action === 'edit') onEditPlace?.(place);
            };
          });
        });

        const marker = new mapboxgl.Marker({ color: '#2563eb' })
          .setLngLat([lng, lat])
          .setPopup(popup)
          .addTo(mapRef.current);

        markersRef.current.push(marker);
      });

    },
    [user, onTagPlace, onEditPlace],
  );

  useEffect(() => {
    if (!mapReady) return;

    const params = {
      q: filters.q || undefined,
      hechsher_id: filters.hechshers.length ? filters.hechshers.map((h) => h.hechsher_id) : undefined,
      tags: filters.tags.length ? filters.tags : undefined,
      radius: filters.radius,
      unit: filters.unit,
      lat: filters.lat ?? undefined,
      lng: filters.lng ?? undefined,
      location_query: filters.locationQuery || undefined,
    };

    getPlaces(params)
      .then(({ data }) => {
        const items = Array.isArray(data?.items) ? data.items : [];
        return renderMarkers(items);
      })
      .catch((error) => {
        console.error(error);
      });
  }, [mapReady, filters, renderMarkers]);

  return <div ref={mapContainer} className="map-container" />;
}

