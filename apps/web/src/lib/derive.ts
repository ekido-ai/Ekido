// Turns the raw event stream into what the screen shows. Pure, so replay and live behave identically.
// Event format: docs/schemas/events.schema.json

export type FeedEvent = {
  id: number;
  ts: string;
  type: string;
  job_id: string | null;
  provenance: "LIVE" | "RECORDED" | "SYNTHETIC";
  data: Record<string, any>;
};

export type Provider = {
  provider_id: string;
  name: string;
  kind: "REAL" | "CAPPED_PROFILE" | "INJECTED_FAULT";
  status: string;
  capacity_mib: number | null;
  price_per_step: string;
  gpu_model?: string | null;
};

export type Checkpoint = { hash: string; step: number; state: "VERIFIED" | "ACCEPTED" | "REJECTED"; reason?: string | null; segment: number };

export type Segment = {
  index: number;
  provider: string;
  from: number;
  to: number;
  rejected: boolean;
  ended: boolean;
  // Steps after the last usable checkpoint, which a failure throws away.
  lostFrom: number | null;
};

export type QualityRound = {
  checkpoint: string;
  verdict: string;
  accuracy: number | null;
  difference: number | null;
  ciLower: number | null;
  margin: number | null;
  isFinal: boolean;
  againstBaseline: boolean;
  reasons: string[];
  votes: { verifier: string; verdict: string }[];
  step: number | null;
};

export type Decision = { decision: string; code: string | null; reason: string; exec: any };
export type Tx = { action: string; tx_hash: string | null; status: string; explorer_url: string | null; local_chain: boolean };
export type StageRow = { stage: string; detail: string; ts: string };
export type Telemetry = { util_pct: number | null; mem_used_mib: number | null; temp_c: number | null; power_w: number | null; source: string };

export type View = {
  state: string;
  step: number;
  total: number;
  activeProvider: string | null;
  segments: Segment[];
  checkpoints: Checkpoint[];
  quality: QualityRound[];
  decisions: Record<string, Decision>;
  txs: Tx[];
  stages: StageRow[];
  loss: { step: number; loss: number; provider: string; segment: number }[];
  telemetry: Telemetry | null;
  stepsPerS: number | null;
  peakMib: number | null;
  lostSteps: number | null;
  failure: { provider: string | null; cause: string; injected: boolean } | null;
  lastRejection: { step: number; provider: string | null; reason: string; accuracy: number | null } | null;
  recovering: boolean;
  recoveryCause: "failure" | "rejection" | null;
  faults: string[];
};

export function derive(events: FeedEvent[], fallbackTotal = 400): View {
  const view: View = {
    state: "OPEN", step: 0, total: fallbackTotal, activeProvider: null, segments: [], checkpoints: [], quality: [], decisions: {}, txs: [], stages: [],
    loss: [], telemetry: null, stepsPerS: null, peakMib: null, lostSteps: null, failure: null, lastRejection: null, recovering: false, recoveryCause: null, faults: [],
  };
  const byHash = new Map<string, Checkpoint>();
  const rounds = new Map<string, QualityRound>();

  const accepted = () => view.checkpoints.reduce((best, c) => (c.state === "ACCEPTED" && c.step > best ? c.step : best), 0);

  for (const event of events) {
    const d = event.data;
    switch (event.type) {
      case "job.state_changed":
        view.state = d.to;
        if (d.to === "RUNNING") view.recovering = false;
        if (d.to === "RECOVERING") {
          view.recovering = true;
          const current = view.segments.at(-1);
          if (current) current.ended = true;
        }
        break;
      case "training.progress": {
        view.total = d.total_steps ?? view.total;
        const step = d.step ?? 0;
        let current = view.segments.at(-1);
        // A replaced worker's last messages can still arrive. They mustn't look like new work.
        if (current?.ended && current.provider === d.provider_id) break;
        if (!current || current.provider !== d.provider_id || current.ended || step < current.to) {
          const resumeAt = accepted();
          if (current && current.to > resumeAt && !current.rejected) current.lostFrom = resumeAt;
          if (current) current.ended = true;
          current = { index: view.segments.length, provider: d.provider_id, from: view.segments.length ? resumeAt : 0, to: step, rejected: false, ended: false, lostFrom: null };
          view.segments.push(current);
        }
        current.to = Math.max(current.to, step);
        view.step = step;
        view.activeProvider = d.provider_id;
        if (typeof d.steps_per_s === "number") view.stepsPerS = d.steps_per_s;
        if (typeof d.peak_mem_mib === "number") view.peakMib = d.peak_mem_mib;
        if (typeof d.loss === "number") view.loss.push({ step, loss: d.loss, provider: d.provider_id, segment: current.index });
        break;
      }
      case "checkpoint.committed":
      case "checkpoint.verified":
      case "checkpoint.accepted":
      case "checkpoint.rejected": {
        let checkpoint = byHash.get(d.checkpoint_hash);
        if (!checkpoint) {
          checkpoint = { hash: d.checkpoint_hash, step: d.step, state: "VERIFIED", segment: Math.max(0, view.segments.length - 1) };
          byHash.set(d.checkpoint_hash, checkpoint);
          view.checkpoints.push(checkpoint);
        }
        if (event.type === "checkpoint.accepted") checkpoint.state = "ACCEPTED";
        if (event.type === "checkpoint.rejected") {
          checkpoint.state = "REJECTED";
          checkpoint.reason = d.reason;
          const segment = view.segments[checkpoint.segment];
          if (segment) {
            segment.rejected = true;
            // A rejected attempt's other checkpoints can't be trusted either.
            for (const other of view.checkpoints) if (other.segment === segment.index && other.state !== "ACCEPTED") other.state = "REJECTED";
          }
          view.lastRejection = { step: d.step, provider: segment?.provider ?? null, reason: d.reason, accuracy: rounds.get(d.checkpoint_hash)?.accuracy ?? null };
          view.recoveryCause = "rejection";
        }
        break;
      }
      case "quality.result": {
        let round = rounds.get(d.checkpoint_hash);
        if (!round) {
          round = {
            checkpoint: d.checkpoint_hash, verdict: d.verdict, accuracy: d.accuracy, difference: d.difference, ciLower: d.ci_lower, margin: d.margin, isFinal: !!d.is_final,
            // Older recordings lack the field. A jump this large can only be against the untrained model.
            againstBaseline: d.against_baseline ?? (typeof d.difference === "number" && d.difference > 0.3),
            reasons: d.reasons ?? [], votes: [], step: byHash.get(d.checkpoint_hash)?.step ?? null,
          };
          rounds.set(d.checkpoint_hash, round);
          view.quality.push(round);
        }
        round.verdict = d.verdict;
        round.votes.push({ verifier: d.verifier, verdict: d.verdict });
        break;
      }
      case "compile.decision":
        if (d.provider_id === "__proto__" || d.provider_id === "constructor" || d.provider_id === "prototype") break;
        view.decisions[d.provider_id] = { decision: d.decision, code: d.code, reason: d.reason, exec: d.exec };
        break;
      case "recovery.step":
        view.stages.push({ stage: d.stage, detail: d.detail, ts: event.ts });
        if (typeof d.lost_steps === "number") view.lostSteps = d.lost_steps;
        break;
      case "failure.detected":
        view.failure = { provider: d.provider_id ?? null, cause: d.cause, injected: !!d.injected };
        view.recoveryCause = "failure";
        break;
      case "fault.injected":
        view.faults.push(d.fault_kind);
        break;
      case "chain.tx":
        view.txs.push({ action: d.action, tx_hash: d.tx_hash, status: d.status, explorer_url: d.explorer_url, local_chain: !!d.local_chain });
        break;
      case "telemetry.sample":
        view.telemetry = { util_pct: d.util_pct, mem_used_mib: d.mem_used_mib, temp_c: d.temp_c, power_w: d.power_w, source: d.source };
        break;
    }
  }
  return view;
}

// Steps each provider contributed to the accepted chain. Rejected attempts and lost tails count for nothing.
export function acceptedSteps(view: View): Record<string, number> {
  const totals: Record<string, number> = {};
  const usable = view.segments.filter((s) => !s.rejected);
  usable.forEach((segment, i) => {
    const next = usable[i + 1];
    // Steps past the last usable checkpoint were lost, so they don't count.
    const end = next ? next.from : segment.lostFrom ?? segment.to;
    totals[segment.provider] = (totals[segment.provider] ?? 0) + Math.max(0, end - segment.from);
  });
  return totals;
}

const CAUSES: Record<string, string> = {
  PROCESS_EXIT: "its training process died",
  OOM: "it ran out of GPU memory",
  HEARTBEAT_LOST: "it stopped responding",
  DISCONNECT: "it lost its connection",
  DIVERGED: "its training diverged",
  NO_FINAL_CHECKPOINT: "it finished without a final checkpoint",
  BAD_CHECKPOINT: "it produced a checkpoint that failed its integrity check",
  START_FAILED: "it couldn't start the job",
};

const STAGE_TEXT: Record<string, string> = {
  DETECTED: "Failure detected",
  FENCED: "Blocking the old worker from writing",
  HANDOVER_EVAL: "Checking the last checkpoint before building on it",
  SELECT_CHECKPOINT: "Choosing the checkpoint to resume from",
  FIND_CANDIDATES: "Measuring which providers can take over",
  COMPILE: "Adapting the job to the replacement",
  ASSIGN: "Assigning the replacement",
  RESTORE: "Restoring the checkpoint",
  RESUMED: "Training resumed",
  ABORT: "No provider can take over",
};

export const stageText = (stage: string) => STAGE_TEXT[stage] ?? stage;

export function headline(view: View, name: (id: string | null) => string): string {
  const percent = (value: number | null | undefined) => (typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "unknown");
  const finalRound = [...view.quality].reverse().find((r) => r.isFinal);
  switch (view.state) {
    case "OPEN":
      return "Waiting for a funded job to start.";
    case "ASSIGNED":
      return `${name(view.activeProvider)} is getting ready to train.`;
    case "VALIDATING":
      return "Training finished. Verifiers are checking the final model.";
    case "COMPLETED":
      return `Final model accepted at ${percent(finalRound?.accuracy)} accuracy. Verifiers are signing the payout.`;
    case "SETTLED":
      return `Paid on-chain for accepted work only. Final accuracy ${percent(finalRound?.accuracy)}.`;
    case "REFUNDED":
      return "No provider could finish the job, so the client was refunded in full.";
    case "FAILED":
      return "No provider can finish this job. Refunding the client.";
    case "CANCELLED":
      return "The client cancelled this job before it started.";
  }
  if (view.state === "RECOVERING") {
    const stage = view.stages.at(-1);
    if (view.recoveryCause === "rejection" && view.lastRejection) {
      const next = stage && stage.stage !== "FENCED" && stage.stage !== "HANDOVER_EVAL" ? ` ${stageText(stage.stage)}.` : " Finding someone else.";
      return `${name(view.lastRejection.provider)}'s work was rejected at ${percent(view.lastRejection.accuracy)} accuracy.${next}`;
    }
    const cause = view.failure ? CAUSES[view.failure.cause] ?? "it failed" : "it failed";
    return `${name(view.failure?.provider ?? null)} is out: ${cause}. ${stage ? stageText(stage.stage) + "." : ""}`;
  }
  return `${name(view.activeProvider)} is training: step ${view.step} of ${view.total}.`;
}
