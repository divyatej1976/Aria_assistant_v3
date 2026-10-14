"use client";

export type AssessmentScore = { attempt_id: string; score: number; total: number; completed_at: string };

function completedDate(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : value + "Z");
}

export function AssessmentScoreTrend({ scores }: { scores: AssessmentScore[] }) {
  const ordered = [...new Map(scores.filter(item => Number.isFinite(item.score) && Number.isFinite(item.total) && item.total > 0 && item.score >= 0 && item.score <= item.total && Number.isFinite(completedDate(item.completed_at).getTime()))
    .map(item => [item.attempt_id, item])).values()]
    .sort((a, b) => completedDate(a.completed_at).getTime() - completedDate(b.completed_at).getTime() || a.attempt_id.localeCompare(b.attempt_id))
    .slice(-20);
  if (!ordered.length) return null;
  const points = ordered.map((item, index) => ({ ...item, percent: Math.round(item.score / item.total * 100),
    x: ordered.length === 1 ? 160 : 10 + index * 300 / (ordered.length - 1), y: 86 - item.score / item.total * 72 }));
  const latest = points.at(-1)!;
  return <section className="assessment-score-trend" aria-labelledby="score-trend-heading">
    <div><p className="eyebrow">YOUR PRACTICE OVER TIME</p><h2 id="score-trend-heading">Assessment scores</h2>
      <p className="score-trend-description">{points.length === 1 ? "Your first completed review. Keep practising to build your trend." : `${points.length} recent completed attempts, from oldest to newest.`}</p></div>
    <div className="score-trend-chart">
      <span className="score-trend-scale">100%</span>
      <svg viewBox="0 0 320 100" role="img" aria-label={`Assessment score trend. Latest score ${latest.percent} percent. Scale zero to one hundred percent.`}>
        <path d="M10 14H310M10 86H310" className="score-trend-grid" />
        {points.length > 1 && <polyline points={points.map(point => `${point.x},${point.y}`).join(" ")} className="score-trend-line" />}
        {points.map(point => <circle key={point.attempt_id} cx={point.x} cy={point.y} r="3.5" className="score-trend-point"><title>{point.score}/{point.total} · {point.percent}% · {completedDate(point.completed_at).toLocaleDateString()}</title></circle>)}
      </svg>
      <span className="score-trend-scale">0%</span>
    </div>
    <div className="score-trend-latest"><strong>{latest.percent}%</strong><span>Latest · {latest.score}/{latest.total}</span></div>
    <details className="score-trend-details"><summary>View scores as a list</summary><ol>{points.map(point => <li key={point.attempt_id}>{completedDate(point.completed_at).toLocaleDateString()} · {point.score}/{point.total} ({point.percent}%)</li>)}</ol></details>
  </section>;
}
