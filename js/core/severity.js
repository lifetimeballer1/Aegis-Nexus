/** Shared mapping from canonical artifact fields to presentation severity.
 * Canonical operational language ONLY: info | watch | critical | healthy.
 * Colors communicate state, never decoration (see css/tokens.css --sev-*).
 * - critical: immediate attention (red)
 * - watch: elevated, monitor (amber)
 * - info: informational, normal activity (blue)
 * - healthy: normal operation / validated (green)
 */

export function confidenceSeverity(value) {
  const raw = String(value || '').toLowerCase();
  if (/(health|stable|online|verified)/.test(raw)) return 'healthy';
  if (raw.includes('high') || raw === 'confirmed') return 'critical';
  if (raw.includes('mod') || raw === 'likely' || raw === 'moderate') return 'watch';
  return 'info';
}

export function escalationSeverity(value) {
  const raw = String(value || '').toUpperCase();
  if (/(HEALTH|STABLE|ONLINE)/.test(raw)) return 'healthy';
  if (raw === 'CRITICAL') return 'critical';
  if (raw === 'HIGH' || raw === 'ELEVATED') return 'watch';
  return 'info';
}

export function watchLevelSeverity(value) {
  const raw = String(value || '').toUpperCase();
  if (/(HEALTH|STABLE|ONLINE)/.test(raw)) return 'healthy';
  if (raw === 'CRITICAL') return 'critical';
  if (raw === 'HIGH' || raw === 'ELEVATED' || raw === 'WATCH') return 'watch';
  return 'info';
}
