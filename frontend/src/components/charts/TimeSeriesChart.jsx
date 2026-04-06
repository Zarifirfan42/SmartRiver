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

function buildOptions(titleText) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
      title: {
        display: true,
        text: titleText || 'Station WQI trend',
        font: { size: 14 },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Date', font: { size: 12 } },
        grid: { display: false },
        ticks: { maxTicksLimit: 12 },
      },
      y: {
        title: { display: true, text: 'WQI value', font: { size: 12 } },
        min: 0,
        max: 100,
        grid: { color: '#e2e8f0' },
        ticks: { stepSize: 20 },
      },
    },
  }
}

export default function TimeSeriesChart({ data = [], height = 280, title, subtitle }) {
  const titleText = subtitle ? `${title || 'WQI trend'} — ${subtitle}` : title || 'WQI trend'
  const options = buildOptions(titleText)
  const labels = data.map((d) => d.date || d.label)
  const wqiValues = data.map((d) => d.wqi ?? d.value)

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
      },
    ],
  }

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  )
}
