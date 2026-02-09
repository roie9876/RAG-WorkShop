import { useState, useEffect, useCallback } from 'react'

interface SystemStatus {
  status: string
  pid: number
  uptime_seconds: number
  uptime_formatted: string
  python_version: string
}

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function SystemControls() {
  const [isOpen, setIsOpen] = useState(false)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [restarting, setRestarting] = useState(false)
  const [backendOnline, setBackendOnline] = useState(true)

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/system/status`)
      if (!res.ok) throw new Error()
      setStatus(await res.json())
      setBackendOnline(true)
    } catch {
      setBackendOnline(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) fetchStatus()
  }, [isOpen, fetchStatus])

  // Poll while restarting
  useEffect(() => {
    if (!restarting) return
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/system/health`)
        if (res.ok) {
          setRestarting(false)
          setBackendOnline(true)
          fetchStatus()
        }
      } catch { /* still restarting */ }
    }, 2000)
    return () => clearInterval(interval)
  }, [restarting, fetchStatus])

  const handleRestartBackend = async () => {
    if (!confirm('⚠️ Restart Backend Server?\n\nThis will interrupt any in-progress operations.\nThe page will automatically reconnect when the backend is back online.')) return
    setRestarting(true)
    setBackendOnline(false)
    try { await fetch(`${API}/api/system/restart`, { method: 'POST' }) } catch { /* expected */ }
  }

  return (
    <div className="relative">
      {/* Gear button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`p-2 rounded-lg transition-colors ${isOpen ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100 text-gray-500'} ${!backendOnline && !restarting ? 'text-red-500' : ''}`}
        title="System Controls"
      >
        <svg className={`h-5 w-5 ${restarting ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 top-full mt-2 w-80 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 bg-gray-50 border-b">
              <h3 className="font-semibold text-sm text-gray-700">⚙️ System Controls</h3>
            </div>

            {/* Status */}
            <div className="p-4 border-b">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-500">Backend Status</span>
                {backendOnline ? (
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                    Online
                  </span>
                ) : restarting ? (
                  <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-medium rounded-full flex items-center gap-1">
                    <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}><path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    Restarting...
                  </span>
                ) : (
                  <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs font-medium rounded-full flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full" />
                    Offline
                  </span>
                )}
              </div>

              {status && backendOnline && (
                <div className="space-y-2 text-sm text-gray-500">
                  <div className="flex justify-between">
                    <span>⏱ Uptime</span>
                    <span className="font-mono text-gray-700">{status.uptime_formatted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>🖥 PID</span>
                    <span className="font-mono text-gray-700">{status.pid}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>🐍 Python</span>
                    <span className="font-mono text-gray-700">{status.python_version}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-4 space-y-2">
              <button
                onClick={handleRestartBackend}
                disabled={restarting || !backendOnline}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-orange-50 hover:bg-orange-100 text-orange-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {restarting ? '⟳ Restarting Backend...' : '⏻ Restart Backend'}
              </button>

              <button
                onClick={() => window.location.reload()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium transition-colors text-sm"
              >
                🔄 Refresh Frontend
              </button>

              <button
                onClick={() => {
                  if ('caches' in window) {
                    caches.keys().then(names => names.forEach(n => caches.delete(n)))
                  }
                  window.location.href = window.location.href.split('?')[0] + '?t=' + Date.now()
                }}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-600 font-medium transition-colors text-sm"
              >
                🗑 Hard Refresh (Clear Cache)
              </button>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-gray-50 border-t text-xs text-gray-400 text-center">
              GitHub RAG · Module 8
            </div>
          </div>
        </>
      )}
    </div>
  )
}
