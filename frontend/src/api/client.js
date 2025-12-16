/**
 * API client for communicating with the backend.
 */

const API_BASE = '/api';

export async function fetchStatus() {
  const response = await fetch(`${API_BASE}/status`);
  if (!response.ok) throw new Error('Failed to fetch status');
  return response.json();
}

export async function startContainer() {
  const response = await fetch(`${API_BASE}/start`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start container');
  }
  return response.json();
}

export async function stopContainer() {
  const response = await fetch(`${API_BASE}/stop`, { method: 'POST' });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to stop container');
  }
  return response.json();
}

export async function fetchConfig() {
  const response = await fetch(`${API_BASE}/config`);
  if (!response.ok) throw new Error('Failed to fetch config');
  return response.json();
}

export async function updateConfig(config) {
  const response = await fetch(`${API_BASE}/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to update config');
  }
  return response.json();
}

export async function fetchLogs(tail = 100) {
  const response = await fetch(`${API_BASE}/logs?tail=${tail}`);
  if (!response.ok) throw new Error('Failed to fetch logs');
  return response.json();
}

export async function fetchActivity(limit = 50) {
  const response = await fetch(`${API_BASE}/activity?limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch activity');
  return response.json();
}

export async function resetIdleTimer() {
  const response = await fetch(`${API_BASE}/reset-idle`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to reset idle timer');
  return response.json();
}
