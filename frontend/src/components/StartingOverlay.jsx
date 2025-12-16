/**
 * Full-screen overlay shown when container is starting.
 */
export default function StartingOverlay({ visible, onCancel }) {
  if (!visible) return null;

  return (
    <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-8 max-w-md w-full mx-4 text-center">
        {/* Spinner */}
        <div className="w-16 h-16 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-6"></div>

        <h2 className="text-xl font-semibold text-gray-800 mb-2">
          Starting ComfyUI...
        </h2>

        <p className="text-gray-600 mb-6">
          The container is starting up. This may take a minute.
        </p>

        <div className="space-y-3">
          <a
            href="/comfyui"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full py-2 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Open ComfyUI
          </a>

          {onCancel && (
            <button
              onClick={onCancel}
              className="w-full py-2 px-4 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
            >
              Close
            </button>
          )}
        </div>

        <p className="text-xs text-gray-400 mt-4">
          The page will refresh automatically when ready
        </p>
      </div>
    </div>
  );
}
