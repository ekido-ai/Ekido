"use client";

import { useEffect, useRef, useState } from "react";
import type { FeedEvent, Provider } from "./derive";

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const WS = API.replace(/^http/, "ws");

export type Connection = "connecting" | "online" | "reconnecting" | "unreachable";

// Follows the newest job. A dropped socket reconnects and catches up from the last event it saw.
export function useLiveFeed(enabled: boolean) {
  const [connection, setConnection] = useState<Connection>("connecting");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [events, setEvents] = useState<FeedEvent[]>([]);
  // Events can arrive out of order, because several server threads emit at once. So a lower ID isn't
  // a duplicate: track what's been seen, and only count IDs as caught up when there's no gap below.
  const seen = useRef(new Set<number>());
  const caughtUp = useRef(0);

  const receive = (incoming: FeedEvent[]) => {
    const fresh = incoming.filter((event) => !seen.current.has(event.id));
    if (!fresh.length) return;
    for (const event of fresh) seen.current.add(event.id);
    while (seen.current.has(caughtUp.current + 1)) caughtUp.current += 1;
    setEvents((current) => [...current, ...fresh].sort((a, b) => a.id - b.id));
  };

  useEffect(() => {
    if (!enabled) return;
    let stopped = false;
    const poll = async () => {
      try {
        const [providerList, jobs] = await Promise.all([
          fetch(`${API}/providers`).then((r) => r.json()),
          fetch(`${API}/jobs?limit=1`).then((r) => r.json()),
        ]);
        if (stopped) return;
        setProviders(providerList);
        setConnection((current) => (current === "unreachable" || current === "connecting" ? "online" : current));
        const newest = jobs[0]?.job_id ?? null;
        setJobId((current) => {
          if (newest && newest !== current) {
            seen.current = new Set();
            caughtUp.current = 0;
            setEvents([]);
          }
          return newest ?? current;
        });
      } catch {
        if (!stopped) setConnection("unreachable");
      }
    };
    poll();
    const timer = setInterval(poll, 3000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !jobId) return;
    let socket: WebSocket | null = null;
    let stopped = false;
    let retry: ReturnType<typeof setTimeout>;
    const open = () => {
      socket = new WebSocket(`${WS}/ws/jobs/${jobId}?after=${caughtUp.current}`);
      socket.onopen = () => setConnection("online");
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data);
        if (event.type !== "ping") receive([event]);
      };
      socket.onclose = () => {
        if (stopped) return;
        setConnection("reconnecting");
        retry = setTimeout(open, 1500);
      };
    };
    open();
    // A safety net: anything a socket missed still reaches the screen within a few seconds.
    const fill = setInterval(() => {
      fetch(`${API}/jobs/${jobId}/timeline?after=${caughtUp.current}`).then((r) => r.json()).then(receive).catch(() => {});
    }, 4000);
    return () => {
      stopped = true;
      clearTimeout(retry);
      clearInterval(fill);
      socket?.close();
    };
  }, [enabled, jobId]);

  return { connection, providers, jobId, events };
}

type Recording = { recorded_at: string; note: string; providers: Provider[]; events: FeedEvent[] };

// Plays a recorded real run into the same screen, keeping its real pacing but capping long waits.
export function useReplay(enabled: boolean, speed: number, run: number) {
  const [recording, setRecording] = useState<Recording | null>(null);
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    fetch("/replay.json").then((r) => r.json()).then(setRecording).catch(() => setRecording(null));
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !recording) return;
    setEvents([]);
    setFinished(false);
    let index = 0;
    let timer: ReturnType<typeof setTimeout>;
    const next = () => {
      if (index >= recording.events.length) {
        setFinished(true);
        return;
      }
      const event = recording.events[index++];
      setEvents((current) => [...current, event]);
      const following = recording.events[index];
      const gap = following ? new Date(following.ts).getTime() - new Date(event.ts).getTime() : 0;
      timer = setTimeout(next, Math.min(gap / speed, 1200));
    };
    next();
    return () => clearTimeout(timer);
  }, [enabled, recording, speed, run]);

  return { recording, events, finished };
}
