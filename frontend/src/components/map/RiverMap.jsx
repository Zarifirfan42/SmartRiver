import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'

// Fix default marker icon in Vite/bundler
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
})

function getMarkerColor(statusSlug) {
  if (statusSlug === 'clean') return '#10b981'
  if (statusSlug === 'slightly_polluted') return '#f59e0b'
  return '#ef4444'
}

function StationMarkers({ stations }) {
  return stations.map((s) => (
    <Marker
      key={s.station_code || s.id}
      position={[s.latitude ?? 4.2105, s.longitude ?? 101.9758]}
      icon={defaultIcon}
    >
      <Popup>
        <div className="text-sm">
          <p className="font-semibold">{s.station_name || s.station_code}</p>
          <p>WQI: {s.latest_wqi != null ? Number(s.latest_wqi).toFixed(1) : '—'}</p>
          <p className="capitalize text-surface-600">{s.river_status || '—'}</p>
        </div>
      </Popup>
    </Marker>
  ))
}

export default function RiverMap({ stations = [], center = [4.2105, 101.9758], zoom = 7, height = 320 }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const defaultStations = [
    { station_code: 'S01', station_name: 'Sungai Klang', latitude: 3.1390, longitude: 101.6869, latest_wqi: 72, river_status: 'slightly_polluted' },
    { station_code: 'S02', station_name: 'Sungai Gombak', latitude: 3.2569, longitude: 101.7172, latest_wqi: 85, river_status: 'clean' },
    { station_code: 'S03', station_name: 'Sungai Pinang', latitude: 5.4167, longitude: 100.3333, latest_wqi: 48, river_status: 'polluted' },
  ]

  const list = stations.length ? stations : defaultStations

  if (!mounted) {
    return (
      <div
        className="rounded-xl border border-surface-200 bg-surface-100 flex items-center justify-center text-surface-500"
        style={{ height }}
      >
        Loading map…
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-surface-200 overflow-hidden" style={{ height }}>
      <MapContainer
        center={center}
        zoom={zoom}
        className="h-full w-full"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <StationMarkers stations={list} />
      </MapContainer>
    </div>
  )
}
