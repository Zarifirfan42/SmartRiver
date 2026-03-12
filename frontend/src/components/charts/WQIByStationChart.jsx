/**
 * WQIByStationChart — Bar chart: WQI value per river station.
 * X-axis: River Stations, Y-axis: WQI Value.
 * Uses same station data as River Health page (from API).
 */
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const CHART_TITLE = 'Water Quality Index by Station'
const X_AXIS_LABEL = 'River Stations'
const Y_AXIS_LABEL = 'WQI Value'

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      labels: {
        usePointStyle: true,
      },
    },
    title: {
      display: true,
      text: CHART_TITLE,
      font: { size: 16 },
    },
    tooltip: {
      callbacks: {
        label: (context) => `WQI: ${context.raw}`,
      },
    },
  },
  scales: {
    x: {
      title: {
        display: true,
        text: X_AXIS_LABEL,
        font: { size: 12 },
      },
      grid: { display: false },
      ticks: {
        maxRotation: 45,
        minRotation: 45,
        maxTicksLimit: 20,
      },
    },
    y: {
      title: {
        display: true,
        text: Y_AXIS_LABEL,
        font: { size: 12 },
      },
      min: 0,
      max: 100,
      grid: { color: '#e2e8f0' },
      ticks: { stepSize: 20 },
    },
  },
}

function getBarColor(wqi) {
  if (wqi >= 81) return 'rgba(16, 185, 129, 0.8)'   // eco-500 clean
  if (wqi >= 60) return 'rgba(245, 158, 11, 0.8)'   // amber slightly polluted
  return 'rgba(239, 68, 68, 0.8)'                   // red polluted
}

export default function WQIByStationChart({ stations = [], height = 320 }) {
  const labels = stations.map((s) => s.station_name || s.station_code || 'Unknown')
  const values = stations.map((s) => Number(s.latest_wqi) ?? 0)
  const backgroundColors = values.map(getBarColor)

  const chartData = {
    labels,
    datasets: [
      {
        label: 'WQI',
        data: values,
        backgroundColor: backgroundColors,
        borderColor: backgroundColors.map((c) => c.replace('0.8', '1')),
        borderWidth: 1,
      },
    ],
  }

  if (stations.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-xl border border-surface-200 bg-surface-50 text-surface-500"
        style={{ height }}
      >
        <p>No station data yet. Upload a dataset and run preprocessing to see WQI by station.</p>
      </div>
    )
  }

  return (
    <div>
      <div style={{ height }}>
        <Bar data={chartData} options={options} />
      </div>
      <p className="mt-3 text-xs text-surface-500">
        <span className="inline-block w-2 h-2 rounded-full bg-eco-500 align-middle mr-1" /> Clean (81–100) &nbsp;
        <span className="inline-block w-2 h-2 rounded-full bg-amber-500 align-middle mr-1" /> Slightly polluted (60–80) &nbsp;
        <span className="inline-block w-2 h-2 rounded-full bg-red-500 align-middle mr-1" /> Polluted (0–59)
      </p>
    </div>
  )
}
