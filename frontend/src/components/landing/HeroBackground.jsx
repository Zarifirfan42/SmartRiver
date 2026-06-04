import { useState } from 'react'

export default function HeroBackground() {
  const [videoFailed, setVideoFailed] = useState(false)

  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="landing-wave-bg" />
      <img
        src="/images/river-hero.jpg"
        alt=""
        className="hero-image-bg"
        onError={(e) => {
          e.currentTarget.style.display = 'none'
        }}
      />
      {!videoFailed && (
        <video
          autoPlay
          muted
          loop
          playsInline
          className="hero-video-bg"
          onError={() => setVideoFailed(true)}
        >
          <source src="/videos/river-bg.mp4" type="video/mp4" />
        </video>
      )}
      <div className="hero-overlay" />
    </div>
  )
}
