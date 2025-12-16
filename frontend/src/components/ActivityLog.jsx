import { useState, useEffect } from 'react';
import { fetchActivity } from '../api/client';

/**
 * Activity log showing recent events.
 */
export default function ActivityLog() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);

  const loadEvents = async () => {
    try {
      const data = await fetchActivity(20);
      setEvents(data.events || []);
    } catch (e) {
      console.error('Failed to load activity:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
    const interval = setInterval(loadEvents, 10000);
    return () => clearInterval(interval);
  }, []);

  const getEventIcon = (type) => {
    switch (type) {
      case 'activity':
        return (
          <div className="w-2 h-2 bg-green-500 rounded-full"></div>
        );
      case 'shutdown':
        return (
          <div className="w-2 h-2 bg-red-500 rounded-full"></div>
        );
      case 'system':
        return (
          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
        );
      case 'error':
        return (
          <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
        );
      default:
        return (
          <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
        );
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const displayEvents = expanded ? events : events.slice(0, 5);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Activity Log</h2>
        <button
          onClick={loadEvents}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="text-center py-4 text-gray-500">Loading...</div>
      ) : events.length === 0 ? (
        <div className="text-center py-4 text-gray-500">No recent activity</div>
      ) : (
        <>
          <div className="space-y-3">
            {displayEvents.map((event, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className="mt-1.5">
                  {getEventIcon(event.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700 truncate">{event.message}</p>
                  <p className="text-xs text-gray-400">{formatTime(event.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>

          {events.length > 5 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-4 w-full py-2 text-sm text-gray-600 hover:text-gray-800 border-t"
            >
              {expanded ? 'Show less' : `Show ${events.length - 5} more`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
