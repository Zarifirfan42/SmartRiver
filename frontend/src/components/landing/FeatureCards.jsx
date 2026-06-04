import { useRef } from 'react'

const FEATURES = [
  {
    icon: '🌊',
    title: 'Real-Time WQI Monitoring',
    description: 'Track water quality index live across all stations',
  },
  {
    icon: '🔮',
    title: 'ML Forecast Engine',
    description: 'Predict WQI up to December 2026 using trained ML models',
  },
  {
    icon: '📈',
    title: 'Historical Trends',
    description: 'Analyse river health patterns from 2023 to present',
  },
]

function FeatureCard({ icon, title, description }) {
  const cardRef = useRef(null)

  const handleMove = (e) => {
    const el = cardRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    el.style.transform = `perspective(800px) rotateY(${x * 8}deg) rotateX(${-y * 8}deg) translateY(-8px)`
  }

  const handleLeave = () => {
    const el = cardRef.current
    if (el) el.style.transform = ''
  }

  return (
    <div
      ref={cardRef}
      className="landing-feature-card"
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
    >
      <span className="landing-feature-icon" aria-hidden="true">{icon}</span>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  )
}

export default function FeatureCards() {
  return (
    <section className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className="landing-section-title text-center mb-12">Platform Capabilities</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <FeatureCard key={f.title} {...f} />
          ))}
        </div>
      </div>
    </section>
  )
}
