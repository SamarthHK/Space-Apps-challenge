export function parseApiOrigin(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error('Set VITE_API_BASE_URL to the backend origin.');
  }
  const parts = url.hostname.split('.').map(Number);
  const tailscale = parts.length === 4 && parts[0] === 100 &&
    parts[1] >= 64 && parts[1] <= 127 && parts.every(n => Number.isInteger(n) && n >= 0 && n <= 255);
  const loopback = url.hostname === 'localhost' || url.hostname === '[::1]' ||
    (parts.length === 4 && parts[0] === 127);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash || url.port === '0' || !(tailscale || loopback)) {
    throw new Error('Use an explicit loopback or Tailscale API origin without a path or credentials.');
  }
  return url.origin;
}
