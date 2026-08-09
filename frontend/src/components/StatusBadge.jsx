export default function StatusBadge({ status }) {
  const s = (status || '').toLowerCase()
  const tone =
    ['online', 'streaming', 'live', 'active'].includes(s) ? 'good'
      : ['offline', 'inactive', 'error'].includes(s) ? 'bad'
      : ['reconnecting', 'pending', 'review'].includes(s) ? 'warn'
      : 'neutral'
  return <span className={`badge badge-${tone}`}>{status || 'unknown'}</span>
}
