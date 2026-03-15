/**
 * AlertsBySeverityChart — Bar chart: alert count by severity (critical, warning, info).
 * For FYP demo: clear visualization of alert distribution.
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

const severityOrder = ['critical', 'warning', 'info']
const severityLabels = { critical: 'Critical', warning: 'Warning', info: 'Info' }
const severityColors = {
  critical: 'rgba(239, 68, 68, 0.8)',
  warning: 'rgba(245, 158, 11, 0.8)',
  info: 'rgba(6, 182, 212, 0.8)',
}

export default function AlertsBySeverityChart({ alerts = [], height = 200 }) {
  const counts = severityOrder.map((sev) =>
    alerts.filter((a) => (a.severity || 'info').toLowerCase() === sev).length
  )
  const labels = severityOrder.map((s) => severityLabels[s])
  const backgroundColors = severityOrder.map((s) => severityColors[s])

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Alerts',
        data: counts,
        backgroundColor: backgroundColors,
        borderColor: backgroundColors.map((c) => c.replace('0.8', '1')),
        borderWidth: 1,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: 'Alerts by severity',
        font: { size: 14 },
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `Count: ${ctx.raw}`,
        },
      },
    },
    scales: {
      x: {
        title: { display: true, text: 'Severity' },
        grid: { display: false },
      },
      y: {
        title: { display: true, text: 'Count' },
        min: 0,
        ticks: { stepSize: 1 },
        grid: { color: '#e2e8f0' },
      },
    },
  }

  if (alerts.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-surface-200 bg-surface-50 text-surface-500 text-sm"
        style={{ height }}
      >
        No alerts to display. Alerts are generated when anomalies are detected.
      </div>
    )
  }

  return (
    <div style={{ height }}>
      <Bar data={chartData} options={options} />
    </div>
  )
}
