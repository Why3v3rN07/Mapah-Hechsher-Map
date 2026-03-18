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
            console.log("Places::", places);

            new mapboxgl.Marker({ color: "red" })
                .setLngLat([35.2137, 31.7683])
                .addTo(map);

            places.forEach(place => {
                new mapboxgl.Marker()
                    .setLngLat([place.lng, place.lat])
                    .setPopup(new mapboxgl.Popup().setText(place.name))
                    .addTo(map);
            });
        })


        return () => map.remove();
    }, []);

    return (
        <div
            ref={mapContainer}
            style={{width: "100%", height: "100vh"}}
        />
    );
}
