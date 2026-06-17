import {useEffect, useRef} from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import places from "./data/places.json";

console.log("Places:", places);

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN;

export default function MapView() {
    const mapContainer = useRef(null);

    useEffect(() => {
        const map = new mapboxgl.Map({
            container: mapContainer.current,
            style: "mapbox://styles/mapbox/streets-v12",
            center: [34.8516, 31.0461], // Israel
            zoom: 7,
        });

        map.on("load", () => {
            fetch("http://localhost:5000/api/places")
                .then(res => {
                    console.log("Response status:", res.status, res.statusText);
                    if (!res.ok) {
                        throw new Error(`HTTP error! status: ${res.status}`);
                    }
                    return res.json();
                })
                .then(data => {
                    console.log("Fetched data:", data);
                    if (!data.items || !Array.isArray(data.items)) {
                        console.warn("Expected data.items to be an array, got:", data);
                        return;
                    }
                    console.log(`Adding ${data.items.length} markers to map`);
                    data.items.forEach(place => {
                        if (place.latitude && place.longitude) {
                            console.log(`Adding marker for ${place.place_name} at [${place.longitude}, ${place.latitude}]`);
                            new mapboxgl.Marker()
                                .setLngLat([place.longitude, place.latitude])
                                .setPopup(new mapboxgl.Popup().setText(place.place_name))
                                .addTo(map);
                        } else {
                            console.warn(`Skipping ${place.place_name}: missing coordinates`, place);
                        }
                    });
                })
                .catch(err => console.error("Error fetching places:", err));
        });


        return () => map.remove();
    }, []);

    return (
        <div
            ref={mapContainer}
            style={{width: "100%", height: "100vh"}}
        />
    );
}
