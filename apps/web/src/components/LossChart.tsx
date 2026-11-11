"use client";

import { useState } from "react";
import type { View } from "@/lib/derive";

const W = 640;
const H = 200;
const PAD = { left: 40, right: 12, top: 10, bottom: 26 };

type Props = { view: View; color: (id: string) => string; name: (id: string | null) => string };

export function LossChart({ view, color, name }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const points = view.loss;
  const max = Math.max(1, ...points.map((p) => p.loss));
  const nice = Math.ceil(max * 2) / 2;
  const x = (step: number) => PAD.left + (step / Math.max(view.total, 1)) * (W - PAD.left - PAD.right);
  const y = (loss: number) => H - PAD.bottom - (loss / nice) * (H - PAD.top - PAD.bottom);

  const segments = new Map<number, typeof points>();
  for (const point of points) segments.set(point.segment, [...(segments.get(point.segment) ?? []), point]);
  const providers = [...new Set(points.map((p) => p.provider))];
  const active = hover === null ? null : points[hover];

  const onMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (!points.length) return;
    const box = event.currentTarget.getBoundingClientRect();
    const step = ((event.clientX - box.left) / box.width * W - PAD.left) / (W - PAD.left - PAD.right) * view.total;
    let best = 0;
    points.forEach((p, i) => {
      if (Math.abs(p.step - step) < Math.abs(points[best].step - step)) best = i;
    });
    setHover(best);
  };

  if (!points.length) return <p className="empty">The training loss appears here once a provider starts.</p>;

  return (
    <div className="loss">
      <svg viewBox={`0 0 ${W} ${H}`} onPointerMove={onMove} onPointerLeave={() => setHover(null)} role="img" aria-label={`Training loss per step. Latest value ${points.at(-1)?.loss.toFixed(2)}.`}>
        {[0, nice / 2, nice].map((tick) => (
          <g key={tick}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(tick)} y2={y(tick)} className="grid" />
            <text x={PAD.left - 8} y={y(tick) + 4} textAnchor="end" className="axis">{tick.toFixed(1)}</text>
          </g>
        ))}
        <text x={W - PAD.right} y={H - 6} textAnchor="end" className="axis">step {view.total}</text>
        <text x={PAD.left} y={H - 6} className="axis">step 0</text>
        {[...segments.entries()].map(([segment, line]) => (
          <polyline
            key={segment}
            points={line.map((p) => `${x(p.step)},${y(p.loss)}`).join(" ")}
            fill="none"
            stroke={color(line[0].provider)}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeDasharray={view.segments[segment]?.rejected ? "5 4" : undefined}
          />
        ))}
        {active && (
          <g>
            <line x1={x(active.step)} x2={x(active.step)} y1={PAD.top} y2={H - PAD.bottom} className="crosshair" />
            <circle cx={x(active.step)} cy={y(active.loss)} r={4} fill={color(active.provider)} className="crosshair-dot" />
          </g>
        )}
      </svg>
      <p className="loss-read" aria-live="off">
        {active ? `Step ${active.step}, loss ${active.loss.toFixed(3)}, ${name(active.provider)}` : `Latest loss ${points.at(-1)?.loss.toFixed(3)} at step ${points.at(-1)?.step}`}
      </p>
      {providers.length > 1 && (
        <ul className="legend">
          {providers.map((id) => (
            <li key={id}><span className="swatch" style={{ background: color(id) }} />{name(id)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
