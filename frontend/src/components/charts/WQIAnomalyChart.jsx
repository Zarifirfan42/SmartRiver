import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const options = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { maxTicksLimit: 12 },
    },
    y: {
      min: 0,
      max: 100,
      grid: { color: '#e2e8f0' },
      ticks: { stepSize: 20 },
    },
  },
}

/**
 * WQI time series with anomaly points marked clearly (red dots).
 * data: [{ date, wqi, station_code? }]
 * anomalies: [{ date, station_code, wqi, reason }]
 */
export default function WQIAnomalyChart({ data = [], anomalies = [], height = 320 }) {
  const labels = data.map((d) => d.date || d.label)
  const wqiValues = data.map((d) => d.wqi ?? d.value)

  const anomalyKeySet = new Set(
    (anomalies || []).map((a) => `${String(a.date || '').trim()}|${String(a.station_code || '').trim()}`)
  )
  const anomalyValues = data.map((d, i) => {
    const key = `${String(d.date || '').trim()}|${String(d.station_code || '').trim()}`
    return anomalyKeySet.has(key) ? (d.wqi ?? d.value) : null
  })

  const chartData = {
    labels,
    datasets: [
      {
        label: 'WQI',
        data: wqiValues,
        borderColor: '#0891b2',
        backgroundColor: 'rgba(6, 182, 212, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
      },
      {
        label: 'Anomaly (abnormal spike)',
        data: anomalyValues,
        borderColor: 'transparent',
        backgroundColor: '#dc2626',
        fill: false,
        pointRadius: 6,
        pointHoverRadius: 8,
        pointStyle: 'circle',
        order: 0,
      },
    ],
  }

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  )
}
