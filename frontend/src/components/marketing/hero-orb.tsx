import { useState } from 'react'
import { Activity, BrainCircuit, ChartNoAxesCombined, Sparkles } from 'lucide-react'

const SIGNALS = [
  { id: 'evidence', label: 'Evidence mapped', icon: Sparkles, position: 'one' },
  { id: 'patterns', label: 'Patterns compared', icon: ChartNoAxesCombined, position: 'two' },
  { id: 'review', label: 'Human review ready', icon: Activity, position: 'three' },
] as const

/** A lightweight, interactive CSS 3D constellation for the hero. */
export function HeroOrb() {
  const [activeSignal, setActiveSignal] = useState('evidence')
  const active = SIGNALS.find((signal) => signal.id === activeSignal) ?? SIGNALS[0]

  return (
    <div className="hero-orb" aria-label="Interactive intelligence constellation">
      <div className="hero-orb__halo hero-orb__halo--one" />
      <div className="hero-orb__halo hero-orb__halo--two" />
      <div className="hero-orb__scene">
        <button type="button" className="hero-orb__string hero-orb__string--one" aria-label="Select evidence signal" onClick={() => setActiveSignal('evidence')} />
        <button type="button" className="hero-orb__string hero-orb__string--two" aria-label="Select pattern signal" onClick={() => setActiveSignal('patterns')} />
        <button type="button" className="hero-orb__string hero-orb__string--three" aria-label="Select review signal" onClick={() => setActiveSignal('review')} />
        <div className="hero-orb__ring hero-orb__ring--x" />
        <div className="hero-orb__ring hero-orb__ring--y" />
        <div className="hero-orb__ring hero-orb__ring--z" />
        <button type="button" className="hero-orb__core" onClick={() => setActiveSignal('evidence')} aria-label="Select central intelligence signal">
          <span className="hero-orb__core-shine" />
          <BrainCircuit className="hero-orb__core-icon" />
        </button>
        {SIGNALS.map(({ id, icon: Icon, position, label }) => (
          <button
            type="button"
            key={id}
            className={`hero-orb__node hero-orb__node--${position}${activeSignal === id ? ' is-active' : ''}`}
            onClick={() => setActiveSignal(id)}
            aria-label={label}
            aria-pressed={activeSignal === id}
          >
            <Icon />
          </button>
        ))}
      </div>
      <div className="hero-orb__label hero-orb__label--top">{active.label} <span /></div>
      <div className="hero-orb__label hero-orb__label--bottom">Tap a signal <span /></div>
    </div>
  )
}
