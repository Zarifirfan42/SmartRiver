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

function formatRiverStatus(status) {
  if (!status) return '—'
  const s = String(status).toLowerCase()
  if (s === 'clean') return 'Clean'
  if (s === 'slightly_polluted' || s === 'slightly polluted') return 'Slightly polluted'
  if (s === 'polluted') return 'Polluted'
  return status.replace(/_/g, ' ')
}

function StationMarkers({ stations, onStationClick }) {
  return stations.map((s) => (
    <Marker
      key={s.station_code || s.id}
      position={[s.latitude ?? 4.2105, s.longitude ?? 101.9758]}
      icon={defaultIcon}
      eventHandlers={
        onStationClick
          ? {
              click: () => onStationClick(s),
            }
          : undefined
      }
    >
      <Popup>
        <div className="min-w-[180px] text-sm">
          <p className="font-semibold text-surface-900 border-b border-surface-200 pb-1.5 mb-2">
            Station name
          </p>
          <p className="text-surface-800">{s.station_name || s.station_code || '—'}</p>
          <p className="font-semibold text-surface-900 border-b border-surface-200 pb-1.5 mt-3 mb-2">
            Latest WQI
          </p>
          <p className="text-surface-800">
            {s.latest_wqi != null ? Number(s.latest_wqi).toFixed(1) : '—'}
          </p>
          <p className="font-semibold text-surface-900 border-b border-surface-200 pb-1.5 mt-3 mb-2">
            River status
          </p>
          <p className="text-surface-800 capitalize">
            {formatRiverStatus(s.river_status)}
          </p>
          {onStationClick && (
            <button
              type="button"
              className="mt-3 w-full rounded-lg bg-river-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-river-700"
              onClick={() => onStationClick(s)}
            >
              View chart & table →
            </button>
          )}
        </div>
      </Popup>
    </Marker>
  ))
}

export default function RiverMap({ stations = [], center = [4.2105, 101.9758], zoom = 7, height = 320, onStationClick, useDefaultStations = true }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const defaultStations = [
    { station_code: 'S01', station_name: 'Sungai Klang', latitude: 3.1390, longitude: 101.6869, latest_wqi: 72, river_status: 'slightly_polluted' },
    { station_code: 'S02', station_name: 'Sungai Gombak', latitude: 3.2569, longitude: 101.7172, latest_wqi: 85, river_status: 'clean' },
    { station_code: 'S03', station_name: 'Sungai Pinang', latitude: 5.4167, longitude: 100.3333, latest_wqi: 48, river_status: 'polluted' },
  ]

  const list = stations.length ? stations : (useDefaultStations ? defaultStations : [])

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
        <StationMarkers stations={list} onStationClick={onStationClick} />
      </MapContainer>
    </div>
  )
}
