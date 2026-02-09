import { useState, useEffect, useCallback } from 'react'
import { Settings, RefreshCw, Power, Clock, Server, Monitor } from 'lucide-react'
import { systemApi, type SystemStatus } from '../services/api'

export function SystemControls() {
  const [isOpen, setIsOpen] = useState(false)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [restarting, setRestarting] = useState(false)
  const [backendOnline, setBackendOnline] = useState(true)

  const fetchStatus = useCallback(async () => {
    try {
      const data = await systemApi.getStatus()
      setStatus(data)
      setBackendOnline(true)
    } catch (error) {
      console.error('Failed to fetch system status:', error)
      setBackendOnline(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      fetchStatus()
    }
  }, [isOpen, fetchStatus])

  // Poll for backend status when restarting
  useEffect(() => {
    if (!restarting) return

    const checkBackend = async () => {
      try {
        await systemApi.getHealth()
        setRestarting(false)
        setBackendOnline(true)
        fetchStatus()
      } catch {
        // Still restarting, keep polling
      }
    }

    const interval = setInterval(checkBackend, 2000)
    return () => clearInterval(interval)
  }, [restarting, fetchStatus])

  const handleRestartBackend = async () => {
    if (!confirm('⚠️ Restart Backend Server?\n\nThis will interrupt any in-progress operations.\nThe page will automatically reconnect when the backend is back online.')) {
      return
    }

    setRestarting(true)
    setBackendOnline(false)
    
    try {
      await systemApi.restartBackend()
    } catch (error) {
      // Expected - the request will fail as the server shuts down
      console.log('Backend restart initiated')
    }
  }

  const handleRefreshFrontend = () => {
    window.location.reload()
  }

  const handleHardRefresh = () => {
    // Clear cache and reload
    if ('caches' in window) {
      caches.keys().then((names) => {
        names.forEach((name) => {
          caches.delete(name)
        })
      })
    }
    window.location.href = window.location.href.split('?')[0] + '?t=' + Date.now()
  }

  return (
    <div className="relative">
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`p-2 rounded-lg transition-colors ${
          isOpen ? 'bg-primary/10 text-primary' : 'hover:bg-muted text-muted-foreground'
        } ${!backendOnline ? 'text-red-500' : ''}`}
        title="System Controls"
      >
        <Settings className={`h-5 w-5 ${restarting ? 'animate-spin' : ''}`} />
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Panel */}
          <div className="absolute right-0 top-full mt-2 w-80 bg-card border rounded-xl shadow-lg z-50 overflow-hidden">
            {/* Header */}
            <div className="px-4 py-3 bg-muted/50 border-b">
              <h3 className="font-semibold flex items-center gap-2">
                <Settings className="h-4 w-4" />
                System Controls
              </h3>
            </div>

            {/* Status */}
            <div className="p-4 border-b">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-muted-foreground">Backend Status</span>
                {backendOnline ? (
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                    Online
                  </span>
                ) : restarting ? (
                  <span className="px-2 py-0.5 bg-orange-100 text-orange-700 text-xs font-medium rounded-full flex items-center gap-1">
                    <RefreshCw className="h-3 w-3 animate-spin" />
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
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="flex items-center gap-2">
                      <Clock className="h-3.5 w-3.5" />
                      Uptime
                    </span>
                    <span className="font-mono">{status.uptime_formatted}</span>
                  </div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="flex items-center gap-2">
                      <Server className="h-3.5 w-3.5" />
                      Process ID
                    </span>
                    <span className="font-mono">{status.pid}</span>
                  </div>
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="flex items-center gap-2">
                      <Monitor className="h-3.5 w-3.5" />
                      Python
                    </span>
                    <span className="font-mono">{status.python_version}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-4 space-y-2">
              <button
                onClick={handleRestartBackend}
                disabled={restarting || !backendOnline}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-orange-50 hover:bg-orange-100 text-orange-700 font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {restarting ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Power className="h-4 w-4" />
                )}
                {restarting ? 'Restarting Backend...' : 'Restart Backend'}
              </button>

              <button
                onClick={handleRefreshFrontend}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 font-medium transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh Frontend
              </button>

              <button
                onClick={handleHardRefresh}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-muted hover:bg-muted/80 text-muted-foreground font-medium transition-colors text-sm"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Hard Refresh (Clear Cache)
              </button>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 bg-muted/30 border-t text-xs text-muted-foreground text-center">
              RAG Workshop Pipeline v1.1.0
            </div>
          </div>
        </>
      )}
    </div>
  )
}
