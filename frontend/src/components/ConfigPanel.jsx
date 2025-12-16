import { useState, useEffect } from 'react';

/**
 * Configuration panel for manager settings.
 */
export default function ConfigPanel({ config, onSave, loading }) {
  const [localConfig, setLocalConfig] = useState({
    idle_timeout_minutes: 30,
    auto_start_enabled: true,
    container_name: 'comfyui',
  });
  const [hasChanges, setHasChanges] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    if (config) {
      setLocalConfig({
        idle_timeout_minutes: config.idle_timeout_minutes || 30,
        auto_start_enabled: config.auto_start_enabled ?? true,
        container_name: config.container_name || 'comfyui',
      });
    }
  }, [config]);

  const handleChange = (field, value) => {
    setLocalConfig(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
    setMessage(null);
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      await onSave(localConfig);
      setHasChanges(false);
      setMessage({ type: 'success', text: 'Settings saved!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (e) {
      setMessage({ type: 'error', text: e.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Settings</h2>

      {/* Idle Timeout */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Idle Timeout: {localConfig.idle_timeout_minutes} minutes
        </label>
        <input
          type="range"
          min="5"
          max="120"
          step="5"
          value={localConfig.idle_timeout_minutes}
          onChange={(e) => handleChange('idle_timeout_minutes', parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>5 min</span>
          <span>1 hour</span>
          <span>2 hours</span>
        </div>
      </div>

      {/* Auto Start */}
      <div className="mb-6">
        <label className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Auto-start on access</span>
          <button
            onClick={() => handleChange('auto_start_enabled', !localConfig.auto_start_enabled)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              localConfig.auto_start_enabled ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                localConfig.auto_start_enabled ? 'translate-x-6' : ''
              }`}
            ></span>
          </button>
        </label>
        <p className="text-xs text-gray-500 mt-1">
          Automatically start the container when someone accesses ComfyUI
        </p>
      </div>

      {/* Container Name */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Container Name
        </label>
        <input
          type="text"
          value={localConfig.container_name}
          onChange={(e) => handleChange('container_name', e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="comfyui"
        />
        <p className="text-xs text-gray-500 mt-1">
          The Docker container name to manage
        </p>
      </div>

      {/* Save Button */}
      {hasChanges && (
        <button
          onClick={handleSave}
          disabled={saving || loading}
          className={`w-full py-2 px-4 rounded-md font-medium text-white transition-colors ${
            saving || loading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      )}

      {/* Message */}
      {message && (
        <div className={`mt-4 p-3 rounded-md text-sm ${
          message.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  );
}
