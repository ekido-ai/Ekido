"use client";

import type { View } from "@/lib/derive";

const WIDTH = 1200;
const LEFT = 26;
const RIGHT = 26;
const MAIN_Y = 92;
const BRANCH_Y = 172;
const LOST_Y = 40;

type Props = { view: View; color: (id: string) => string; name: (id: string | null) => string; live: boolean };

// The chain of training work, drawn as a circuit trace. Accepted work stays on the main line.
// Rejected work drops off it and is cut, which is the whole payment rule in one picture.
export function Rail({ view, color, name, live }: Props) {
  const total = Math.max(view.total, 1);
  const x = (step: number) => LEFT + (Math.min(step, total) / total) * (WIDTH - LEFT - RIGHT);
  const ticks = Array.from({ length: 5 }, (_, i) => Math.round((total * i) / 4));
  const usable = view.segments.filter((s) => !s.rejected);

  const describe = view.segments
    .map((s) => `${name(s.provider)} from step ${s.from} to ${s.to}${s.rejected ? ", rejected" : ""}`)
    .join("; ");

  return (
    <figure className="rail">
      <svg viewBox={`0 0 ${WIDTH} 226`} role="img" aria-label={describe ? `Training work so far: ${describe}.` : "No training work yet."}>
        <defs>
          <pattern id="rejected-hatch" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="4.5" height="9" fill="var(--status-bad)" />
          </pattern>
        </defs>

        {/* Where the job still has to go. */}
        <line x1={x(0)} x2={x(total)} y1={MAIN_Y} y2={MAIN_Y} className="rail-remaining" />
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={MAIN_Y + 12} y2={MAIN_Y + 20} className="rail-tick" />
            <text x={x(tick)} y={MAIN_Y + 38} textAnchor={tick === total ? "end" : "middle"} className="rail-tick-label">
              {tick === total ? `${tick} steps` : tick}
            </text>
          </g>
        ))}

        {/* Rejected attempts leave the main line at 45 degrees and end in a cut. */}
        {view.segments.filter((s) => s.rejected).map((s) => {
          const start = x(s.from);
          const drop = BRANCH_Y - MAIN_Y;
          const end = Math.max(x(s.to), start + drop + 40);
          return (
            <g key={`rejected-${s.index}`}>
              <path d={`M ${start} ${MAIN_Y} L ${start + drop} ${BRANCH_Y} L ${end} ${BRANCH_Y}`} fill="none" stroke="url(#rejected-hatch)" strokeWidth={9} />
              <g transform={`translate(${end + 12} ${BRANCH_Y})`} className="rail-cut">
                <line x1={-7} y1={-7} x2={7} y2={7} />
                <line x1={-7} y1={7} x2={7} y2={-7} />
              </g>
              <text x={start + drop + 6} y={BRANCH_Y + 26} className="rail-note">
                {name(s.provider)}: rejected, earns nothing
              </text>
            </g>
          );
        })}

        {/* Steps done after the last usable checkpoint, lost when the provider died. */}
        {view.segments.filter((s) => s.lostFrom !== null && s.to > (s.lostFrom ?? 0) && !s.rejected).map((s, i, lost) => {
          const start = x(s.lostFrom ?? 0);
          const rise = MAIN_Y - LOST_Y;
          return (
            <g key={`lost-${s.index}`}>
              <path d={`M ${start} ${MAIN_Y} L ${start + rise} ${LOST_Y} L ${Math.max(x(s.to) + rise, start + rise + 16)} ${LOST_Y}`} fill="none" className="rail-lost" stroke={color(s.provider)} />
              {/* Only the latest note, so several failures can't print on top of each other. */}
              {i === lost.length - 1 && (
                <text x={start + rise + 22} y={LOST_Y - 10} className="rail-note">
                  {s.to - (s.lostFrom ?? 0)} steps lost when {name(s.provider)} died
                </text>
              )}
            </g>
          );
        })}

        {/* The accepted line. */}
        {usable.map((s, i) => {
          const next = usable[i + 1];
          const end = next ? next.from : s.lostFrom ?? s.to;
          return (
            <g key={`segment-${s.index}`}>
              <line x1={x(s.from)} x2={x(end)} y1={MAIN_Y} y2={MAIN_Y} stroke={color(s.provider)} className="rail-trace" />
              {x(end) - x(s.from) > 90 && (
                <text x={(x(s.from) + x(end)) / 2} y={MAIN_Y - 16} textAnchor="middle" className="rail-label">
                  {name(s.provider)}
                </text>
              )}
            </g>
          );
        })}

        {/* Checkpoints: gold-plated vias once accepted, open pads until then. */}
        {view.checkpoints.filter((c) => c.state !== "REJECTED").map((c) => (
          <circle key={c.hash} cx={x(c.step)} cy={MAIN_Y} r={c.state === "ACCEPTED" ? 9 : 4.5} className={c.state === "ACCEPTED" ? "via via-accepted" : "via"}>
            <title>{`Checkpoint at step ${c.step}: ${c.state === "ACCEPTED" ? "accepted by verifiers" : "saved, not yet evaluated"}`}</title>
          </circle>
        ))}

        {live && view.state === "RUNNING" && <circle cx={x(view.step)} cy={MAIN_Y} r={7} className="rail-head" />}
      </svg>
      <figcaption className="rail-key">
        <span><svg width="22" height="14" aria-hidden="true"><circle cx="11" cy="7" r="6" className="via via-accepted" /></svg>Verifiers accepted this checkpoint</span>
        <span><svg width="22" height="14" aria-hidden="true"><circle cx="11" cy="7" r="4" className="via" /></svg>Saved, not yet evaluated</span>
      </figcaption>
    </figure>
  );
}
