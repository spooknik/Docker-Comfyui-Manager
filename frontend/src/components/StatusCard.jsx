/**
 * Status card showing container state with visual indicator.
 */
export default function StatusCard({ container, onStart, onStop, loading }) {
  const state = container?.state || 'unknown';
  const isRunning = state === 'running';
  const isStarting = state === 'starting';
  const isStopping = state === 'stopping';
  const isStopped = state === 'stopped';

  const getStatusColor = () => {
    switch (state) {
      case 'running': return 'bg-green-500';
      case 'starting': return 'bg-yellow-500 animate-pulse';
      case 'stopping': return 'bg-yellow-500 animate-pulse';
      case 'stopped': return 'bg-gray-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-400';
    }
  };

  const getStatusText = () => {
    switch (state) {
      case 'running': return 'Running';
      case 'starting': return 'Starting...';
      case 'stopping': return 'Stopping...';
      case 'stopped': return 'Stopped';
      case 'error': return 'Error';
      case 'not_found': return 'Not Found';
      default: return 'Unknown';
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Container Status</h2>
        <div className="flex items-center gap-2">
          <span className={`w-3 h-3 rounded-full ${getStatusColor()}`}></span>
          <span className="text-sm font-medium text-gray-600">{getStatusText()}</span>
        </div>
      </div>

      {container?.container_name && (
        <div className="mb-4 text-sm text-gray-600">
          <span className="font-medium">Container:</span> {container.container_name}
        </div>
      )}

      {container?.started_at && isRunning && (
        <div className="mb-4 text-sm text-gray-600">
          <span className="font-medium">Started:</span>{' '}
          {new Date(container.started_at).toLocaleString()}
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onStart}
          disabled={loading || isRunning || isStarting}
          className={`flex-1 py-2 px-4 rounded-md font-medium text-white transition-colors
            ${isRunning || isStarting || loading
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700'
            }`}
        >
          {isStarting ? 'Starting...' : 'Start'}
        </button>
        <button
          onClick={onStop}
          disabled={loading || isStopped || isStopping}
          className={`flex-1 py-2 px-4 rounded-md font-medium text-white transition-colors
            ${isStopped || isStopping || loading
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-red-600 hover:bg-red-700'
            }`}
        >
          {isStopping ? 'Stopping...' : 'Stop'}
        </button>
      </div>

      {state === 'not_found' && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <p className="text-sm text-yellow-800">
            Container not found. Make sure the container name is correct in settings.
          </p>
        </div>
      )}
    </div>
  );
}
