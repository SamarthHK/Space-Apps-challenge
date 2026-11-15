export function createResource(onChange = () => {}) {
  let generation = 0;
  let controller = null;
  let state = { status: 'idle', data: null, error: null, requestKey: null };
  const publish = next => { state = next; onChange(state); };
  return {
    get state() { return state; },
    clear() {
      generation++;
      controller?.abort();
      publish({ status: 'idle', data: null, error: null, requestKey: null });
    },
    async load(requestKey, request) {
      const current = ++generation;
      controller?.abort();
      controller = new AbortController();
      publish({ status: 'loading', data: null, error: null, requestKey });
      try {
        const data = await request(controller.signal);
        if (current === generation) {
          const empty = Array.isArray(data?.data) && data.data.length === 0;
          publish({ status: empty ? 'empty' : 'ready', data, error: null, requestKey });
        }
      } catch (error) {
        if (current === generation) publish({ status: 'error', data: null, error, requestKey });
      }
    },
  };
}
