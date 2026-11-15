"use client";

import { useEffect, useMemo, useState } from "react";
import { LossChart } from "@/components/LossChart";
import { Rail } from "@/components/Rail";
import { acceptedSteps, derive, headline, stageText, type Provider, type View } from "@/lib/derive";
import { API, useLiveFeed, useReplay } from "@/lib/useFeed";

const COLORS = ["#BA850F", "#E2569C", "#2E98E0", "#7E8F86"];

const KIND_LABEL: Record<Provider["kind"], string> = {
  REAL: "Real GPU",
  CAPPED_PROFILE: "Capped profile, same GPU",
  INJECTED_FAULT: "Injected fault",
};

function shortAddress(value: string) {
  return `${value.slice(0, 6)}…${value.slice(-4)}`;
}

function percent(value: number | null | undefined, digits = 1) {
  return typeof value === "number" ? `${(value * 100).toFixed(digits)}%` : "Unknown";
}

function points(value: number | null | undefined) {
  if (typeof value !== "number") return "unknown";
  const shown = (value * 100).toFixed(1);
  return `${value >= 0 ? "+" : "−"}${shown.replace("-", "")} points`;
}

function reading(value: number | null | undefined, unit: string) {
  return typeof value === "number" ? `${Math.round(value)}${unit}` : "Unknown";
}

export default function Home() {
  const [mode, setMode] = useState<"live" | "replay" | null>(null);
  const [run, setRun] = useState(0);
  const speed = 3;

  useEffect(() => {
    const wanted = new URLSearchParams(window.location.search).get("mode");
    setMode(wanted === "replay" ? "replay" : "live");
  }, []);

  const live = useLiveFeed(mode === "live");
  const replay = useReplay(mode === "replay", speed, run);

  const isLive = mode === "live";
  const events = isLive ? live.events : replay.events;
  const providers = isLive ? live.providers : replay.recording?.providers ?? [];
  const view: View = useMemo(() => derive(events), [events]);

  const ordered = useMemo(() => {
    // Colour follows the provider, in the order they first appear, and never changes during a run.
    const seen = view.segments.map((s) => s.provider);
    return [...new Set([...seen, ...providers.map((p) => p.provider_id)])];
  }, [view.segments, providers]);
  const color = (id: string) => COLORS[Math.max(0, ordered.indexOf(id)) % COLORS.length];
  const provider = (id: string | null) => providers.find((p) => p.provider_id === id);
  const name = (id: string | null) => provider(id)?.name.replace(/\s*\(.*\)$/, "") ?? "A provider";

  const chainTx = view.txs.filter((t) => t.tx_hash);
  const localChain = view.txs.some((t) => t.local_chain);

  if (mode === null) return null;

  return (
    <main className="page">
      <header className="top">
        <p className="brand">Ekido</p>
        <div className="truth">
          {!isLive && <span className="badge badge-warn">Recorded run{replay.recording ? `, ${replay.recording.recorded_at}` : ""}</span>}
          {isLive && events.some((e) => e.provenance === "SYNTHETIC") && <span className="badge badge-warn">Synthetic CPU workload</span>}
          {localChain && <span className="badge">Local test chain</span>}
          <span className="badge">Verifiers run by our team</span>
          {isLive ? (
            <button className="link" onClick={() => setMode("replay")}>Watch the recorded run</button>
          ) : (
            <button className="link" onClick={() => setMode("live")}>Go live</button>
          )}
        </div>
      </header>

      {isLive && live.connection === "unreachable" && (
        <div className="notice" role="alert">
          Can&apos;t reach the coordinator at {API}. Start it with <code>python experiments/demo_stack.py</code>, or watch the recorded run.
        </div>
      )}
      {isLive && live.connection === "reconnecting" && <div className="notice" role="status">Connection lost. Reconnecting, and no events will be missed.</div>}

      <section className="lead">
        <h1 aria-live="polite">{headline(view, name)}</h1>
        <div className="lead-actions">
          {isLive ? <KillButton jobId={live.jobId} state={view.state} target={view.state === "RUNNING" ? view.activeProvider : null} name={name} /> : (
            <button className="button" onClick={() => setRun((r) => r + 1)}>{replay.finished ? "Play again" : "Restart"}</button>
          )}
        </div>
      </section>

      <Rail view={view} color={color} name={name} live={isLive || !replay.finished} />

      <div className="columns">
        <section aria-labelledby="providers-title">
          <h2 id="providers-title">Providers</h2>
          {!providers.length && <p className="empty">No providers connected yet. Each one appears here once its agent joins.</p>}
          <ul className="providers">
            {providers.map((p) => {
              const decision = view.decisions[p.provider_id];
              const running = view.activeProvider === p.provider_id && view.state === "RUNNING";
              return (
                <li key={p.provider_id} className={running ? "provider provider-running" : "provider"}>
                  <div className="provider-head">
                    <span className="swatch" style={{ background: color(p.provider_id) }} />
                    <strong>{name(p.provider_id)}</strong>
                    <span className={p.kind === "REAL" ? "badge" : "badge badge-warn"}>{KIND_LABEL[p.kind]}</span>
                  </div>
                  <p className="meta">
                    {p.capacity_mib ? `${p.capacity_mib} MiB limit` : "Full GPU memory"}, {Number(p.price_per_step)} USDC a step
                  </p>
                  {decision && (
                    decision.decision === "ACCEPTED" && decision.exec ? (
                      <p className="meta strong">Runs at {decision.exec.micro_batch} × {decision.exec.accumulation}, {decision.exec.amp.toUpperCase()}</p>
                    ) : decision.decision === "REJECTED" ? (
                      <p className="meta status-bad"><span aria-hidden="true">✕ </span>Refused: {decision.reason}</p>
                    ) : null
                  )}
                </li>
              );
            })}
          </ul>
        </section>

        <section aria-labelledby="quality-title">
          <h2 id="quality-title">Quality check</h2>
          {!view.quality.length && <p className="empty">Verifiers check a replacement&apos;s first work, and the final model, against a held-out test set.</p>}
          <ul className="rounds">
            {[...view.quality].reverse().slice(0, 3).map((round) => (
              <li key={round.checkpoint} className="round">
                <div className="round-head">
                  <span className={round.verdict === "PASS" ? "verdict verdict-pass" : "verdict verdict-fail"}>
                    <span aria-hidden="true">{round.verdict === "PASS" ? "✓ " : "✕ "}</span>{round.verdict === "PASS" ? "Passed" : "Rejected"}
                  </span>
                  <span className="meta">{round.isFinal ? "Final model" : round.step ? `Step ${round.step}` : "Checkpoint"}</span>
                </div>
                <p className="accuracy">{percent(round.accuracy)}<span> accuracy</span></p>
                <p className="meta">
                  Change from {round.againstBaseline ? "the untrained model" : "the last accepted model"}: {points(round.difference)}. Worst case at 95% confidence: {points(round.ciLower)}, and the limit is {points(round.margin === null ? null : -round.margin)}.
                </p>
                <p className="meta">{round.votes.length} of 2 verifiers agree</p>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby="payout-title">
          <h2 id="payout-title">Payout</h2>
          <Payout view={view} providers={providers} color={color} name={name} />
          {chainTx.length > 0 && (
            <ol className="txs">
              {chainTx.map((t) => (
                <li key={t.tx_hash}>
                  <span>{{ markActive: "Job started", anchorEvent: "Recovery recorded", submitAttestation: "Verifier verdict", finalize: "Paid out" }[t.action] ?? t.action}</span>
                  {t.explorer_url ? <a href={t.explorer_url} target="_blank" rel="noreferrer">{shortAddress(t.tx_hash!)}</a> : <code>{shortAddress(t.tx_hash!)}</code>}
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <div className="columns columns-wide">
        <section aria-labelledby="training-title">
          <h2 id="training-title">Training loss</h2>
          <LossChart view={view} color={color} name={name} />
        </section>

        <section aria-labelledby="gpu-title">
          <h2 id="gpu-title">{isLive && !["SETTLED", "REFUNDED", "CANCELLED"].includes(view.state) ? "GPU right now" : "GPU at last reading"}</h2>
          <dl className="readings">
            <div><dt>Temperature</dt><dd>{reading(view.telemetry?.temp_c, "°C")}</dd></div>
            <div><dt>Memory in use</dt><dd>{reading(view.telemetry?.mem_used_mib, " MiB")}</dd></div>
            <div><dt>Power</dt><dd>{reading(view.telemetry?.power_w, " W")}</dd></div>
            <div><dt>Speed</dt><dd>{typeof view.stepsPerS === "number" ? `${view.stepsPerS.toFixed(1)} steps/s` : "Unknown"}</dd></div>
          </dl>
          <p className="meta">Reported by the provider&apos;s own software, so it&apos;s never used to decide payment.</p>
          {view.stages.length > 0 && (
            <>
              <h3>Recovery steps</h3>
              <ol className="stages">
                {view.stages.slice(-6).map((stage, i) => <li key={`${stage.ts}-${i}`}>{stageText(stage.stage)}</li>)}
              </ol>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

function Payout({ view, providers, color, name }: { view: View; providers: Provider[]; color: (id: string) => string; name: (id: string | null) => string }) {
  const steps = acceptedSteps(view);
  const paid = view.state === "SETTLED";
  const finished = ["COMPLETED", "SETTLED"].includes(view.state);
  const rejected = view.segments.filter((s) => s.rejected).map((s) => s.provider);
  const rows = [...new Set([...Object.keys(steps), ...rejected])];
  if (!rows.length) return <p className="empty">Payment follows accepted steps, and it&apos;s worked out once training begins.</p>;
  const total = rows.reduce((sum, id) => sum + (rejected.includes(id) && !steps[id] ? 0 : steps[id] ?? 0) * Number(providers.find((p) => p.provider_id === id)?.price_per_step ?? 0), 0);
  return (
    <>
      <p className="meta strong">{paid ? "Paid on-chain" : finished ? "Awaiting verifier signatures" : "If this work is accepted"}</p>
      <table className="payout">
        <thead><tr><th scope="col">Provider</th><th scope="col">Accepted steps</th><th scope="col">USDC</th></tr></thead>
        <tbody>
          {rows.map((id) => {
            const count = rejected.includes(id) ? 0 : steps[id] ?? 0;
            const amount = count * Number(providers.find((p) => p.provider_id === id)?.price_per_step ?? 0);
            return (
              <tr key={id}>
                <th scope="row"><span className="swatch" style={{ background: color(id) }} />{name(id)}</th>
                <td>{count}</td>
                <td>{amount.toFixed(3)}</td>
              </tr>
            );
          })}
          <tr className="total"><th scope="row">Total</th><td /><td>{total.toFixed(3)}</td></tr>
        </tbody>
      </table>
      <p className="meta">The rest of the budget goes back to the client.</p>
    </>
  );
}

function idleLabel(state: string) {
  if (state === "RECOVERING") return "Recovering";
  if (["ASSIGNED", "OPEN"].includes(state)) return "Waiting for training";
  if (state === "VALIDATING") return "Training finished";
  return "Job finished";
}

function KillButton({ jobId, state, target, name }: { jobId: string | null; state: string; target: string | null; name: (id: string | null) => string }) {
  const [armed, setArmed] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!armed) return;
    const timer = setTimeout(() => setArmed(false), 4000);
    return () => clearTimeout(timer);
  }, [armed]);

  const press = async () => {
    if (!armed) {
      setArmed(true);
      return;
    }
    setArmed(false);
    try {
      const response = await fetch(`${API}/demo/faults`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_id: jobId, kind: "KILL_CONTAINER" }) });
      const result = response.ok ? await response.json() : null;
      if (!response.ok) setMessage(`The kill wasn't delivered (error ${response.status}). Check that DEMO_MODE is on.`);
      else setMessage(result.delivered ? null : "The kill wasn't delivered: no provider is running this job right now.");
    } catch {
      setMessage("The kill wasn't delivered: the coordinator can't be reached.");
    }
  };

  return (
    <div className="kill">
      <button className={armed ? "button button-kill armed" : "button button-kill"} disabled={!target} onClick={press}>
        {!target ? idleLabel(state) : armed ? `Press again to kill ${name(target)}` : `Kill ${name(target)}`}
      </button>
      {target && <p className="meta">This really stops the provider&apos;s process.</p>}
      {message && <p className="meta status-bad" role="alert">{message}</p>}
    </div>
  );
}
