import { parseApiOrigin } from '../config.js';

export class ApiError extends Error {
  constructor(code, message, { status = null, requestId = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

export function createClient(origin, { fetcher = fetch, timeoutMs = 15000, validate = () => true } = {}) {
  const base = parseApiOrigin(origin);
  return {
    async get(path, { params = {}, signal, schema } = {}) {
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
      try {
        const response = await fetcher(url, {
          signal: controller.signal, credentials: 'omit', cache: 'no-store',
          redirect: 'error', headers: { Accept: 'application/json' },
        });
        const requestId = response.headers.get('X-Request-ID');
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
          throw new ApiError(valid && body.error?.code || 'request_failed',
            valid && body.error?.message || 'Backend request failed.', { status: response.status, requestId });
        }
        if (!body?.meta || body.meta.api_version !== 'v1' || !Object.hasOwn(body, 'data') ||
            (schema && !validate(schema, body))) {
          throw new ApiError('invalid_response', 'Backend response does not match the pinned API contract.', { requestId });
        }
        return body;
      } catch (error) {
        if (controller.signal.aborted) {
          throw new ApiError(timedOut ? 'timeout' : 'aborted', timedOut ? 'Backend request timed out.' : 'Request cancelled.');
        }
        if (error instanceof ApiError) throw error;
        throw new ApiError('network_error', 'Backend is unreachable. Check the API and Tailscale connection.');
      } finally {
        clearTimeout(timer);
        signal?.removeEventListener('abort', abort);
      }
    },
  };
}
