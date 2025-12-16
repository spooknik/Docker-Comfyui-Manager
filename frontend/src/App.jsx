import { useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { startContainer, stopContainer, updateConfig } from './api/client';
import StatusCard from './components/StatusCard';
import QueueStatus from './components/QueueStatus';
import ConfigPanel from './components/ConfigPanel';
import ActivityLog from './components/ActivityLog';
import StartingOverlay from './components/StartingOverlay';

function App() {
  const { status, connected } = useWebSocket();
  const [loading, setLoading] = useState(false);
  const [showStarting, setShowStarting] = useState(false);

  const handleStart = useCallback(async () => {
    setLoading(true);
    try {
      await startContainer();
      setShowStarting(true);
    } catch (e) {
      alert('Failed to start container: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleStop = useCallback(async () => {
    if (!confirm('Are you sure you want to stop ComfyUI?')) return;
    setLoading(true);
    try {
      await stopContainer();
    } catch (e) {
      alert('Failed to stop container: ' + e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSaveConfig = useCallback(async (config) => {
    await updateConfig(config);
  }, []);

  // Hide starting overlay when container is running
  const containerRunning = status?.container?.state === 'running';
  if (showStarting && containerRunning && status?.queue?.connected) {
    setShowStarting(false);
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">ComfyUI Manager</h1>
              <p className="text-sm text-gray-500 mt-1">
                Automatic container management for ComfyUI
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              <span className="text-sm text-gray-600">
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Quick Actions */}
        {containerRunning && (
          <div className="mb-6">
            <a
              href="/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              Open ComfyUI
            </a>
          </div>
        )}

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Status Card */}
          <StatusCard
            container={status?.container}
            onStart={handleStart}
            onStop={handleStop}
            loading={loading}
          />

          {/* Queue Status */}
          <QueueStatus
            queue={status?.queue}
            idle={status?.idle}
          />

          {/* Config Panel */}
          <ConfigPanel
            config={status?.config}
            onSave={handleSaveConfig}
            loading={loading}
          />
        </div>

        {/* Activity Log - Full Width */}
        <div className="mt-6">
          <ActivityLog />
        </div>

        {/* Info Banner */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-3">
            <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-medium">How it works</p>
              <p className="mt-1">
                The manager monitors ComfyUI's queue. When no jobs are running for the configured
                timeout period, it automatically stops the container to save resources. When someone
                accesses ComfyUI, it automatically starts back up.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <p className="text-sm text-gray-500 text-center">
            ComfyUI Docker Manager - Automatically manages your ComfyUI container on TrueNAS
          </p>
        </div>
      </footer>

      {/* Starting Overlay */}
      <StartingOverlay
        visible={showStarting}
        onCancel={() => setShowStarting(false)}
        comfyuiUrl="/comfyui"
      />
    </div>
  );
}

export default App;
