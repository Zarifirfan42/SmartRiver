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

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const PALETTE = ['#4f46e5', '#0d9488', '#c026d3', '#ea580c', '#64748b', '#b45309']

function toYmd(d) {
  if (!d) return ''
  const s = String(d).trim().slice(0, 10)
  return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : ''
}

/**
 * Multi-station WQI on one timeline (from /dashboard/compare-series).
 */
export default function CompareStationsChart({ compareResult, height = 320 }) {
  const blocks = compareResult?.stations || []
  const dateSet = new Set()
  blocks.forEach((b) => {
    ;(b.series || []).forEach((p) => {
      const y = toYmd(p.date)
      if (y) dateSet.add(y)
    })
  })
  const labels = [...dateSet].sort()

  const datasets = blocks.map((b, i) => {
    const byDate = new Map((b.series || []).map((p) => [toYmd(p.date), p.wqi]))
    const color = PALETTE[i % PALETTE.length]
    return {
      label: `${b.station_code}${b.river_name ? ` · ${b.river_name}` : ''}`,
      data: labels.map((d) => (byDate.has(d) ? byDate.get(d) : null)),
      borderColor: color,
      backgroundColor: `${color}33`,
      borderWidth: 2,
      fill: false,
      tension: 0.2,
      pointRadius: 2,
      spanGaps: false,
    }
  })

  const chartData = { labels, datasets }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'top', labels: { usePointStyle: true } },
      title: {
        display: true,
        text: 'Comparative WQI (historical readings)',
        font: { size: 14 },
      },
      tooltip: {
        callbacks: {
          label(ctx) {
            const v = ctx.parsed.y
            if (v == null || Number.isNaN(v)) return `${ctx.dataset.label}: —`
            return `${ctx.dataset.label}: ${Number(v).toFixed(1)}`
          },
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Date' },
        ticks: { maxTicksLimit: 18, autoSkip: true },
        grid: { display: false },
      },
      y: {
        title: { display: true, text: 'WQI' },
        min: 0,
        max: 100,
        grid: { color: '#e2e8f0' },
      },
    },
  }

  if (!labels.length || !datasets.length) {
    return (
      <div
        className="flex items-center justify-center text-sm text-surface-500 border border-dashed border-surface-200 rounded-lg bg-surface-50"
        style={{ height }}
      >
        Select at least two stations with data and load the chart.
      </div>
    )
  }

  return (
    <div style={{ height }}>
      <Line data={chartData} options={options} />
    </div>
  )
}
