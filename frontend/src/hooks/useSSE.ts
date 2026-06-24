import { useEffect, useRef, useState, useCallback } from "react";
import type { SseEvent } from "../api/types";

const SSE_ENDPOINT = "/api/sse/tickets";

interface UseSSEOptions {
  onEvent?: (event: SseEvent) => void;
  enabled?: boolean;
}

export function useSSE({ onEvent, enabled = true }: UseSSEOptions = {}) {
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  const open = useCallback(() => {
    if (eventSourceRef.current) eventSourceRef.current.close();
    const es = new EventSource(SSE_ENDPOINT);
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);
    es.onerror = () => {
      setConnected(false);
      es.close();
    };
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SseEvent;
        handlerRef.current?.(data);
      } catch {
        /* ignore malformed payloads */
      }
    };
  }, []);

  useEffect(() => {
    if (!enabled) return;
    open();
    return () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      setConnected(false);
    };
  }, [enabled, open]);

  const reconnect = useCallback(() => {
    open();
  }, [open]);

  return { connected, reconnect };
}
