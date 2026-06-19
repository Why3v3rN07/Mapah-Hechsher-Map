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
const SOURCE_ID = 'places-source';
const CLUSTER_LAYER_ID = 'places-clusters';
const CLUSTER_COUNT_LAYER_ID = 'places-cluster-count';
const POINT_LAYER_ID = 'places-unclustered';
const PIN_IMAGE_ID = 'places-pin-icon';

const EMPTY_GEOJSON = {
  type: 'FeatureCollection',
  features: [],
};

function makePinImageData() {
  const width = 44;
  const height = 56;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  ctx.clearRect(0, 0, width, height);

  // Pin head
  ctx.fillStyle = '#2563eb';
  ctx.beginPath();
  ctx.arc(width / 2, 18, 14, 0, Math.PI * 2);
  ctx.fill();

  // Pin tail
  ctx.beginPath();
  ctx.moveTo(width / 2, 52);
  ctx.lineTo(width / 2 - 9, 28);
  ctx.lineTo(width / 2 + 9, 28);
  ctx.closePath();
  ctx.fill();

  // White center dot for contrast
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.arc(width / 2, 18, 5, 0, Math.PI * 2);
  ctx.fill();

  return ctx.getImageData(0, 0, width, height);
}

export default function MapView({ onTagPlace, onEditPlace }) {
  const mapContainer = useRef(null);
  const mapRef = useRef(null);
  const placesByIdRef = useRef(new Map());
  const { filters } = useFilters();
  const { user } = useAuth();
  const userRef = useRef(user);
  const onTagPlaceRef = useRef(onTagPlace);
  const onEditPlaceRef = useRef(onEditPlace);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    userRef.current = user;
  }, [user]);

  useEffect(() => {
    onTagPlaceRef.current = onTagPlace;
  }, [onTagPlace]);

  useEffect(() => {
    onEditPlaceRef.current = onEditPlace;
  }, [onEditPlace]);

  const buildPopupHtml = useCallback(
    (place) => {
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
      const editBtn = userRef.current
        ? `<button class="popup-action-btn" data-action="edit" data-id="${place.place_id}">✏️ Edit</button>`
        : '';

      return `
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
    },
    [],
  );

  const bindPopupActions = useCallback(
    (popup, place) => {
      popup.on('open', () => {
        const popupEl = popup.getElement();
        popupEl?.querySelectorAll('[data-action]').forEach((btn) => {
          btn.onclick = () => {
            const action = btn.dataset.action;
            if (action === 'tag') onTagPlaceRef.current?.(place);
            if (action === 'edit') onEditPlaceRef.current?.(place);
          };
        });
      });
    },
    [],
  );

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

      if (!map.hasImage(PIN_IMAGE_ID)) {
        const pinImage = makePinImageData();
        if (pinImage) {
          map.addImage(PIN_IMAGE_ID, pinImage, { pixelRatio: 2 });
        }
      }

      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: EMPTY_GEOJSON,
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      });

      map.addLayer({
        id: CLUSTER_LAYER_ID,
        type: 'circle',
        source: SOURCE_ID,
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#2563eb',
          'circle-radius': ['step', ['get', 'point_count'], 18, 10, 24, 30, 30],
          'circle-opacity': 0.8,
        },
      });

      map.addLayer({
        id: CLUSTER_COUNT_LAYER_ID,
        type: 'symbol',
        source: SOURCE_ID,
        filter: ['has', 'point_count'],
        layout: {
          'text-field': ['get', 'point_count_abbreviated'],
          'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
          'text-size': 12,
        },
        paint: { 'text-color': '#ffffff' },
      });

      map.addLayer({
        id: POINT_LAYER_ID,
        type: 'symbol',
        source: SOURCE_ID,
        filter: ['!', ['has', 'point_count']],
        layout: {
          'icon-image': PIN_IMAGE_ID,
          'icon-size': 1,
          'icon-anchor': 'bottom',
          'icon-allow-overlap': true,
        },
      });

      map.on('click', CLUSTER_LAYER_ID, (e) => {
        const feature = e.features?.[0];
        const clusterId = feature?.properties?.cluster_id;
        if (!feature || clusterId == null) return;

        const source = map.getSource(SOURCE_ID);
        const coordinates = feature.geometry?.coordinates;
        if (!source || !Array.isArray(coordinates)) return;

        source.getClusterExpansionZoom(clusterId, (err, zoom) => {
          if (err) return;
          map.easeTo({ center: coordinates, zoom, duration: 300 });
        });
      });

      map.on('click', POINT_LAYER_ID, (e) => {
        const feature = e.features?.[0];
        const placeId = Number(feature?.properties?.place_id);
        if (!Number.isFinite(placeId)) return;

        const place = placesByIdRef.current.get(placeId);
        if (!place) return;

        const coordinates = feature.geometry?.coordinates;
        if (!Array.isArray(coordinates)) return;

        const popup = new mapboxgl.Popup({ offset: 15 })
          .setLngLat(coordinates)
          .setHTML(buildPopupHtml(place))
          .addTo(map);
        bindPopupActions(popup, place);
      });

      map.on('mouseenter', CLUSTER_LAYER_ID, () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', CLUSTER_LAYER_ID, () => {
        map.getCanvas().style.cursor = '';
      });
      map.on('mouseenter', POINT_LAYER_ID, () => {
        map.getCanvas().style.cursor = 'pointer';
      });
      map.on('mouseleave', POINT_LAYER_ID, () => {
        map.getCanvas().style.cursor = '';
      });

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

  const updateGeoJsonSource = useCallback((places) => {
    if (!mapRef.current) return;
    const source = mapRef.current.getSource(SOURCE_ID);
    if (!source) return;

    placesByIdRef.current = new Map(places.map((place) => [place.place_id, place]));

    const features = places
      .filter((place) => place.latitude != null && place.longitude != null)
      .map((place) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [Number(place.longitude), Number(place.latitude)],
        },
        properties: {
          place_id: place.place_id,
        },
      }))
      .filter((feature) => {
        const [lng, lat] = feature.geometry.coordinates;
        return Number.isFinite(lat) && Number.isFinite(lng);
      });

    source.setData({
      type: 'FeatureCollection',
      features,
    });
  }, []);

  const fetchPlacesInView = useCallback(() => {
    if (!mapRef.current || !mapReady) return;

    const bounds = mapRef.current.getBounds();
    if (!bounds) return;

    const params = {
      q: filters.q || undefined,
      hechsher_id: filters.hechshers.length ? filters.hechshers.map((h) => h.hechsher_id) : undefined,
      tags: filters.tags.length ? filters.tags : undefined,
      bbox: `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`,
    };

    getPlaces(params)
      .then(({ data }) => {
        const items = Array.isArray(data?.items) ? data.items : [];
        updateGeoJsonSource(items);
      })
      .catch((error) => {
        console.error(error);
      });
  }, [mapReady, filters, updateGeoJsonSource]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    fetchPlacesInView();
    mapRef.current.on('moveend', fetchPlacesInView);

    return () => {
      mapRef.current?.off('moveend', fetchPlacesInView);
    };
  }, [mapReady, fetchPlacesInView]);

  return <div ref={mapContainer} className="map-container" />;
}

