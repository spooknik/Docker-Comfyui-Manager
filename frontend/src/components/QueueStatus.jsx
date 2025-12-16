/**
 * Queue status display showing ComfyUI job information.
 */
export default function QueueStatus({ queue, idle }) {
  const isActive = queue?.is_active || false;
  const connected = queue?.connected || false;
  const running = queue?.running || 0;
  const pending = queue?.pending || 0;
  const totalJobs = queue?.total_jobs || 0;

  const idleMinutes = idle?.idle_minutes || 0;
  const remainingMinutes = idle?.remaining_minutes || 0;
  const timeoutMinutes = idle?.timeout_minutes || 30;

  // Calculate progress for idle timer
  const progressPercent = Math.max(0, Math.min(100, (remainingMinutes / timeoutMinutes) * 100));

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Queue Status</h2>

      {!connected ? (
        <div className="text-center py-4">
          <div className="text-gray-400 mb-2">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3" />
            </svg>
          </div>
          <p className="text-sm text-gray-500">Not connected to ComfyUI</p>
          <p className="text-xs text-gray-400 mt-1">Container may be stopped</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center">
              <div className={`text-3xl font-bold ${running > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                {running}
              </div>
              <div className="text-xs text-gray-500 mt-1">Running</div>
            </div>
            <div className="text-center">
              <div className={`text-3xl font-bold ${pending > 0 ? 'text-yellow-600' : 'text-gray-400'}`}>
                {pending}
              </div>
              <div className="text-xs text-gray-500 mt-1">Pending</div>
            </div>
            <div className="text-center">
              <div className={`text-3xl font-bold ${totalJobs > 0 ? 'text-blue-600' : 'text-gray-400'}`}>
                {totalJobs}
              </div>
              <div className="text-xs text-gray-500 mt-1">Total</div>
            </div>
          </div>

          {/* Activity indicator */}
          <div className={`flex items-center justify-center gap-2 py-2 px-4 rounded-full text-sm mb-4
            ${isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
            <span className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></span>
            {isActive ? 'Processing jobs' : 'Idle'}
          </div>

          {/* Idle timer */}
          <div className="mt-4">
            <div className="flex justify-between text-sm text-gray-600 mb-2">
              <span>Idle Timer</span>
              <span>{Math.round(remainingMinutes)} min remaining</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-1000 ${
                  remainingMinutes < 5 ? 'bg-red-500' :
                  remainingMinutes < 10 ? 'bg-yellow-500' : 'bg-blue-500'
                }`}
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
            <div className="text-xs text-gray-400 mt-1 text-center">
              Idle for {Math.round(idleMinutes)} minutes / {timeoutMinutes} min timeout
            </div>
          </div>
        </>
      )}
    </div>
  );
}
