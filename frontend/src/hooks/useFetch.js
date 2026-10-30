import { useCallback, useEffect, useState } from 'react';
import { formatApiError } from '../utils/errors';

/** Runs an async loader and tracks loading / error state. `reload()` re-runs it. */
export default function useFetch(loader, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(() => {
    setLoading(true); setError('');
    return loader()
      .then((d) => setData(d))
      .catch((e) => setError(formatApiError(e, 'Could not load data.')))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { run(); }, [run]);
  return { data, loading, error, reload: run, setData };
}
