import { useEffect, useRef, useState } from 'react'
import { wsUrl } from '../api/client.js'

/**
 * Manages a single connection to /api/v1/detections/live with automatic
 * reconnection. Incoming messages are stored per camera.
 */
export default function useLiveChannel(token) {
  const [connected, setConnected] = useState(false)
  const [frames, setFrames] = useState({})
  const [events, setEvents] = useState([])
  const [violations, setViolations] = useState([])
  const wsRef = useRef(null)

  useEffect(() => {
    if (!token) return
    let stopped = false
    let retryTimer = null

    const connect = () => {
      const ws = new WebSocket(wsUrl('/api/v1/detections/live', token))
      wsRef.current = ws

      ws.onopen = () => {
        if (stopped) return
        setConnected(true)
        setEvents((prev) => [...prev.slice(-9), { type: 'system', text: 'Connected to live channel', ts: Date.now() }])
      }

      ws.onmessage = (e) => {
        if (stopped) return
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'frame') {
            setFrames((prev) => ({
              ...prev,
              [msg.camera_id]: { image: msg.image, camera_name: msg.camera_name, vehicle_count: msg.vehicle_count, ts: msg.ts },
            }))
          } else if (msg.type === 'violation') {
            const v = msg.violation
            setViolations((prev) => [v, ...prev].slice(0, 20))
            setEvents((prev) =>
              [...prev.slice(-9), { type: 'violation', text: `${v.violation_type} · ${v.camera_name || v.camera_id}`, ts: Date.now() }]
            )
          } else if (msg.type === 'camera_status') {
            setEvents((prev) => [...prev.slice(-9), { type: 'status', text: `${msg.camera_name} → ${msg.status}`, ts: Date.now() }])
          }
        } catch {
          /* ignore malformed */
        }
      }

      ws.onclose = () => {
        if (stopped) return
        setConnected(false)
        retryTimer = setTimeout(connect, 2500)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      stopped = true
      clearTimeout(retryTimer)
      if (wsRef.current) wsRef.current.close()
    }
  }, [token])

  const subscribe = (cameraId) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'subscribe', camera_id: cameraId }))
    }
  }

  const unsubscribe = (cameraId) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'unsubscribe', camera_id: cameraId }))
    }
  }

  return { connected, frames, events, violations, subscribe, unsubscribe }
}
