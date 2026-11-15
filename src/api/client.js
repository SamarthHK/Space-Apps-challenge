import { parseApiOrigin } from '../config.js';

export class ApiError extends Error {
  constructor(code, message, { status = null, requestId = null, details = [], retryable = false,
    outcomeUncertain = false } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.details = details;
    this.retryable = retryable;
    this.outcomeUncertain = outcomeUncertain;
  }
}

export function createClient(origin, { fetcher = fetch, timeoutMs = 15000, validate = () => true,
  onSessionLost = () => {} } = {}) {
  const base = parseApiOrigin(origin);
  let session = null;
  const client = {
    setSession(value) { session = value; },
    async request(path, { method = 'GET', body: payload, rawBody, responseType = 'json',
      headers = {}, params = {}, signal, schema } = {}) {
      if (!path.startsWith('/') || path.startsWith('//') || path.includes('..') || path.includes('\\')) {
        throw new ApiError('invalid_path', 'Invalid API resource path.');
      }
      const url = new URL(`${base}/api/v1${path}`);
      for (const [key, value] of Object.entries(params)) {
        if (value !== null && value !== undefined && value !== '') url.searchParams.set(key, value);
      }
      const controller = new AbortController();
      let timedOut = false;
      const abort = () => controller.abort();
      signal?.addEventListener('abort', abort, { once: true });
      if (signal?.aborted) controller.abort();
      const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
      const scoped = session?.userId && (!path.startsWith('/auth/') || path === '/auth/logout');
      try {
        const response = await fetcher(url, {
          method, body: rawBody ?? (payload === undefined ? undefined : JSON.stringify(payload)),
          signal: controller.signal, credentials: session ? 'include' : 'omit', cache: 'no-store',
          redirect: 'error', headers: { Accept: 'application/json',
            ...(payload === undefined ? {} : { 'Content-Type': 'application/json' }),
            ...(scoped ? { 'X-Account-ID': session.userId } : {}),
            ...(method !== 'GET' && session?.csrfToken ? { 'X-CSRF-Token': session.csrfToken } : {}),
            ...headers },
        });
        if (scoped && response.status === 401) onSessionLost('unauthenticated');
        const requestId = response.headers.get('X-Request-ID');
        const metadata = { etag: response.headers.get('ETag'), requestId,
          location: response.headers.get('Location'), disposition: response.headers.get('Content-Disposition') };
        if (response.ok && responseType === 'blob') {
          const mediaType = response.headers.get('Content-Type')?.split(';')[0];
          if (!['application/geo+json', 'application/vnd.google-earth.kml+xml',
            'application/vnd.google-earth.kmz'].includes(mediaType) ||
            !/^attachment; filename="[^"\\/\x00-\x1f]+"$/.test(metadata.disposition ?? '')) {
            throw new ApiError('invalid_response', 'Export response has invalid download headers.', { requestId });
          }
          const blob = await response.blob();
          if (!blob.size || blob.size > 32 * 1024 * 1024) {
            throw new ApiError('invalid_response', 'Export response has an invalid size.', { requestId });
          }
          return { body: blob, ...metadata };
        }
        if (response.status === 204 && !schema) return { body: null, ...metadata };
        let body;
        try {
          body = await response.json();
        } catch {
          throw new ApiError('malformed_response', 'Backend returned an invalid JSON response.', {
            status: response.status, requestId,
          });
        }
        if (!response.ok) {
          const valid = validate('ErrorResponse', body);
          if (scoped && valid && ['session_changed', 'csrf_invalid'].includes(body.error?.code)) {
            onSessionLost(body.error.code);
          }
          throw new ApiError(valid && body.error?.code || 'request_failed',
            valid && body.error?.message || 'Backend request failed.', {
              status: response.status, requestId, details: valid ? body.error?.details ?? [] : [],
              retryable: valid && body.error?.retryable === true,
            });
        }
        if (!body?.meta || body.meta.api_version !== 'v1' || !Object.hasOwn(body, 'data') ||
            (schema && !validate(schema, body))) {
          throw new ApiError('invalid_response', 'Backend response does not match the pinned API contract.', { requestId });
        }
        return { body, ...metadata };
      } catch (error) {
        if (controller.signal.aborted) {
          throw new ApiError(timedOut ? 'timeout' : 'aborted',
            timedOut ? 'Backend request timed out.' : 'Request cancelled.', { outcomeUncertain: method !== 'GET' });
        }
        if (error instanceof ApiError) {
          error.outcomeUncertain = method !== 'GET' && (error.status >= 500 ||
            ['invalid_response', 'malformed_response'].includes(error.code));
          throw error;
        }
        throw new ApiError('network_error', 'Backend is unreachable. Check the API and Tailscale connection.',
          { outcomeUncertain: method !== 'GET' });
      } finally {
        clearTimeout(timer);
        signal?.removeEventListener('abort', abort);
      }
    },
    async get(path, options) { return (await client.request(path, { ...options, method: 'GET' })).body; },
  };
  return client;
}
