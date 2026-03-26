import { useCallback, useRef, useState } from "react";
import { getConversion, uploadFile } from "../api/client";
import type { Conversion } from "../types";

export function useConversion() {
  const [conversion, setConversion] = useState<Conversion | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(
    (id: string) => {
      stopPolling();
      let failCount = 0;
      pollRef.current = setInterval(async () => {
        try {
          const res = await getConversion(id);
          failCount = 0;
          setConversion(res.data);
          if (res.data.status === "completed" || res.data.status === "failed") {
            stopPolling();
          }
        } catch {
          failCount++;
          if (failCount >= 3) stopPolling();
        }
      }, 1500);
    },
    [stopPolling]
  );

  const upload = async (file: File, settings: Record<string, string>) => {
    setUploading(true);
    setError(null);
    setConversion(null);
    try {
      const res = await uploadFile(file, settings);
      setConversion(res.data);
      if (res.data.status !== "completed" && res.data.status !== "failed") {
        startPolling(res.data.id);
      }
    } catch (err: any) {
      if (err.code === "ERR_NETWORK" || !err.response) {
        setError("Backend server is not running. Start the backend first.");
      } else if (err.response?.status === 500) {
        setError("Server error. Check that the backend is running on port 8000.");
      } else {
        setError(err.response?.data?.detail || "Upload failed");
      }
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    stopPolling();
    setConversion(null);
    setError(null);
  };

  return { conversion, uploading, error, upload, reset };
}
