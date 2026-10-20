import { useCallback, useEffect, useState } from "react";

/**
 * Generic fetch hook. `fetcher` must be a stable function (wrap with
 * useCallback at the call site if it depends on props) that returns a
 * promise. Exposes { data, loading, error, notProcessed, reload }.
 */
export default function useFetch(fetcher, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notProcessed, setNotProcessed] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    setNotProcessed(false);
    fetcher()
      .then((result) => {
        setData(result);
      })
      .catch((err) => {
        if (err?.notProcessed) {
          setNotProcessed(true);
        } else {
          setError(err?.message || "Failed to load data.");
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, notProcessed, reload: load };
}
