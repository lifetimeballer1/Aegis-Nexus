/** Shared mapping from canonical artifact fields to presentation severity. */

export function confidenceSeverity(value) {
  const raw = String(value || '').toLowerCase();
  if (raw.includes('high') || raw === 'confirmed') return 'critical';
  if (raw.includes('mod') || raw === 'likely') return 'high';
  if (raw.includes('low') || raw === 'limited') return 'medium';
  return 'low';
}

export function escalationSeverity(value) {
  const raw = String(value || '').toUpperCase();
  if (raw === 'CRITICAL') return 'critical';
  if (raw === 'HIGH') return 'high';
  if (raw === 'MODERATE') return 'medium';
  return 'low';
}

export function watchLevelSeverity(value) {
  const raw = String(value || '').toUpperCase();
  if (raw === 'CRITICAL') return 'critical';
  if (raw === 'HIGH' || raw === 'ELEVATED' || raw === 'WATCH') return 'watch';
  return 'info';
}
