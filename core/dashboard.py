#!/usr/bin/env python3
"""
Autoimprove Dashboard — Live visualization of all experiments.

Auto-discovers experiments under experiments/ and renders a dashboard
with an experiment selector. Each experiment gets the same view:
score over time, criterion breakdowns, run history, best prompt.

Usage:
    python3 core/dashboard.py
    python3 core/dashboard.py --port 8501
"""

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

REPO_DIR = Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = REPO_DIR / "experiments"

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Autoimprove Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #faf9f7; color: #2d2a26; padding: 32px; max-width: 1200px; margin: 0 auto; }

  .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 32px; flex-wrap: wrap; gap: 16px; }
  .header h1 { font-size: 28px; font-weight: 700; color: #2d2a26; }
  .badge { background: #c0392b; color: white; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 4px; letter-spacing: 1px; }
  .subtitle { color: #8a8580; font-size: 14px; margin-top: 4px; }

  .experiment-selector { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .experiment-selector label { font-size: 12px; font-weight: 600; color: #8a8580; text-transform: uppercase; letter-spacing: 1px; }
  .exp-btn { border: 2px solid #e0ddd9; background: white; border-radius: 8px; padding: 8px 16px; font-size: 14px; cursor: pointer; color: #2d2a26; transition: all 0.15s; }
  .exp-btn:hover { border-color: #c0784a; color: #c0784a; }
  .exp-btn.active { border-color: #c0784a; background: #c0784a; color: white; font-weight: 600; }

  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
  .stat-card { background: white; border-radius: 12px; padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .stat-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8a8580; margin-bottom: 8px; }
  .stat-value { font-size: 36px; font-weight: 700; }
  .stat-value.green { color: #27ae60; }
  .stat-value.orange { color: #c0784a; }
  .stat-value.neutral { color: #2d2a26; }

  .chart-container { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 32px; }
  .chart-title { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8a8580; margin-bottom: 16px; }
  .chart-container canvas { width: 100% !important; height: 300px !important; }

  .criteria-charts { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 32px; }
  .criteria-chart { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .criteria-chart h3 { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8a8580; margin-bottom: 12px; }
  .criteria-chart canvas { width: 100% !important; height: 160px !important; }

  .table-container { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 32px; overflow-x: auto; }
  .table-container h3 { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8a8580; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; min-width: 600px; }
  th { text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8a8580; padding: 8px 12px; border-bottom: 1px solid #eee; }
  td { padding: 10px 12px; border-bottom: 1px solid #f5f4f2; font-size: 14px; }
  .status-keep { color: #27ae60; font-weight: 600; }
  .status-discard { color: #8a8580; }

  .prompt-container { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .prompt-container h3 { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #8a8580; margin-bottom: 12px; }
  .prompt-text { font-family: 'SF Mono', 'Fira Code', monospace; font-size: 13px; line-height: 1.6; color: #4a4540; white-space: pre-wrap; word-break: break-word; background: #faf9f7; padding: 16px; border-radius: 8px; max-height: 300px; overflow-y: auto; }

  .empty-state { text-align: center; padding: 60px 20px; color: #8a8580; }
  .empty-state h2 { font-size: 20px; margin-bottom: 8px; }

  @media (max-width: 768px) {
    .stats { grid-template-columns: repeat(2, 1fr); }
    .criteria-charts { grid-template-columns: 1fr; }
    body { padding: 16px; }
  }
</style>
</head>
<body>

<div class="header">
  <div>
    <div style="display:flex;align-items:center;gap:12px;">
      <h1>Autoimprove</h1>
      <span class="badge">LIVE</span>
    </div>
    <div class="subtitle" id="subtitle">Loading experiments...</div>
  </div>
  <div class="experiment-selector">
    <label>Experiment</label>
    <div id="exp-buttons"></div>
  </div>
</div>

<div id="content">
  <div class="empty-state"><h2>No data yet</h2><p>Run an experiment cycle to see results here.</p></div>
</div>

<script>
const PALETTE = ['#c0784a','#8e44ad','#2980b9','#27ae60','#d35400','#16a085','#c0392b','#2c3e50'];
const ORANGE = '#c0784a';
const ORANGE_LIGHT = 'rgba(192, 120, 74, 0.15)';

let currentExp = null;
let charts = {};
let experiments = [];

const chartDefaults = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#8a8580' } },
    y: { grid: { color: '#f0efed' }, ticks: { font: { size: 11 }, color: '#8a8580' } }
  }
};

function destroyCharts() {
  Object.values(charts).forEach(c => c.destroy());
  charts = {};
}

function createLineChart(canvasId, label, maxY, color) {
  const ctx = document.getElementById(canvasId).getContext('2d');
  const c = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [{ label, data: [], borderColor: color,
      backgroundColor: color.replace(')', ', 0.12)').replace('rgb', 'rgba'),
      fill: true, tension: 0.3, pointRadius: 5,
      pointBackgroundColor: [], pointBorderColor: color, pointBorderWidth: 2 }] },
    options: { ...chartDefaults, scales: { ...chartDefaults.scales,
      y: { ...chartDefaults.scales.y, min: 0, max: maxY,
           ticks: { ...chartDefaults.scales.y.ticks, stepSize: maxY <= 10 ? 1 : 5 } } } }
  });
  return c;
}

function updateChart(chart, labels, data) {
  chart.data.labels = labels;
  chart.data.datasets[0].data = data;
  let best = -1;
  chart.data.datasets[0].pointBackgroundColor = data.map(v => {
    if (v > best) { best = v; return ORANGE; }
    return '#c4c0bb';
  });
  chart.update('none');
}

function renderContent(data) {
  if (!data || !data.runs || data.runs.length === 0) {
    document.getElementById('content').innerHTML =
      '<div class="empty-state"><h2>No runs yet</h2><p>Start the experiment to see results.</p></div>';
    return;
  }

  const { runs, best_prompt, criteria } = data;
  const labels = runs.map(r => `R${r.run}`);
  const scores = runs.map(r => r.score);
  const baseline = scores[0];
  const best = Math.max(...scores);
  const maxScore = runs[0].max || 40;

  // Stats
  let kept = 0, rb = -1;
  scores.forEach(s => { if (s > rb) { kept++; rb = s; } });
  const improvement = baseline > 0 ? ((best - baseline) / baseline * 100).toFixed(1) : 0;

  // Criteria chart panels
  const criteriaHtml = criteria.map((c, i) => {
    const color = PALETTE[i % PALETTE.length];
    return `<div class="criteria-chart">
      <h3>${c.label}</h3>
      <canvas id="c-chart-${i}"></canvas>
    </div>`;
  }).join('');

  // Table headers
  const critHeaders = criteria.map(c => `<th>${c.label.slice(0,12)}</th>`).join('');
  const batchSize = runs[0] ? (runs[0].max / criteria.length) : 10;

  // Table rows
  let rb2 = -1;
  const rows = runs.map(r => {
    const st = r.score > rb2 ? 'keep' : 'discard';
    if (r.score > rb2) rb2 = r.score;
    const critCells = criteria.map(c =>
      `<td>${r.criteria?.[c.id] ?? '?'}/${batchSize}</td>`
    ).join('');
    const t = r.timestamp ? new Date(r.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
    return `<tr>
      <td>${r.run}</td>
      <td class="status-${st}">${st}</td>
      <td><strong>${r.score}/${maxScore}</strong></td>
      ${critCells}
      <td>${t}</td>
    </tr>`;
  }).reverse().join('');

  document.getElementById('content').innerHTML = `
    <div class="stats">
      <div class="stat-card"><div class="stat-label">Current Best</div>
        <div class="stat-value orange">${best}/${maxScore}</div></div>
      <div class="stat-card"><div class="stat-label">Baseline</div>
        <div class="stat-value neutral">${baseline}/${maxScore}</div></div>
      <div class="stat-card"><div class="stat-label">Improvement</div>
        <div class="stat-value ${improvement > 0 ? 'green' : 'neutral'}">${improvement > 0 ? '+' : ''}${improvement}%</div></div>
      <div class="stat-card"><div class="stat-label">Runs / Kept</div>
        <div class="stat-value neutral">${runs.length} / ${kept}</div></div>
    </div>

    <div class="chart-container">
      <div class="chart-title">Score over time (max ${maxScore})</div>
      <canvas id="main-chart"></canvas>
    </div>

    <div class="criteria-charts">${criteriaHtml}</div>

    <div class="table-container">
      <h3>Run History</h3>
      <table><thead><tr><th>Run</th><th>Status</th><th>Score</th>${critHeaders}<th>Time</th></tr></thead>
      <tbody>${rows}</tbody></table>
    </div>

    <div class="prompt-container">
      <h3>Current Best Prompt</h3>
      <div class="prompt-text">${best_prompt ? escHtml(best_prompt) : '(not yet saved)'}</div>
    </div>
  `;

  destroyCharts();

  // Main chart
  charts['main'] = createLineChart('main-chart', 'Score', maxScore, ORANGE);
  updateChart(charts['main'], labels, scores);

  // Criteria charts
  criteria.forEach((c, i) => {
    const color = PALETTE[i % PALETTE.length];
    const cdata = runs.map(r => r.criteria?.[c.id] ?? 0);
    charts[`c${i}`] = createLineChart(`c-chart-${i}`, c.label, batchSize, color);
    updateChart(charts[`c${i}`], labels, cdata);
  });
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function loadExperiments() {
  const res = await fetch('/api/experiments');
  experiments = await res.json();
  const btns = document.getElementById('exp-buttons');
  btns.innerHTML = experiments.map(e =>
    `<button class="exp-btn" onclick="selectExp('${e.id}')">${e.name}</button>`
  ).join('');
  if (experiments.length > 0) selectExp(experiments[0].id);
}

async function selectExp(id) {
  currentExp = id;
  document.querySelectorAll('.exp-btn').forEach(b => {
    b.classList.toggle('active', b.textContent === (experiments.find(e=>e.id===id)?.name || ''));
  });
  await refresh();
}

async function refresh() {
  if (!currentExp) return;
  try {
    const res = await fetch(`/api/data?experiment=${currentExp}`);
    const data = await res.json();
    const exp = experiments.find(e => e.id === currentExp);
    const n = data.runs?.length || 0;
    const last = data.runs?.[n-1];
    const t = last?.timestamp ? new Date(last.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
    document.getElementById('subtitle').textContent =
      `${exp?.description || currentExp} — ${n} runs${t ? ' — last: ' + t : ''} — refreshes every 15s`;
    renderContent(data);
  } catch(e) {
    console.error(e);
  }
}

loadExperiments();
setInterval(refresh, 15000);
</script>
</body>
</html>"""


def discover_experiments() -> list[dict]:
    """Return list of {id, name, description, data_dir} for all experiments."""
    exps = []
    if not EXPERIMENTS_DIR.exists():
        return exps
    for d in sorted(EXPERIMENTS_DIR.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        data_dir = d / "data"
        config_file = d / "config.yaml"
        if not data_dir.exists():
            continue
        name = d.name
        description = ""
        if config_file.exists():
            try:
                import yaml
                cfg = yaml.safe_load(config_file.read_text())
                name = cfg.get("name", d.name)
                description = cfg.get("description", "")
            except Exception:
                pass
        exps.append({"id": d.name, "name": name, "description": description, "data_dir": data_dir})
    return exps


def get_criteria_meta(exp_id: str) -> list[dict]:
    """Return [{id, label}] from config.yaml, or infer from results."""
    config_file = EXPERIMENTS_DIR / exp_id / "config.yaml"
    if config_file.exists():
        try:
            import yaml
            cfg = yaml.safe_load(config_file.read_text())
            return [{"id": c["id"], "label": c.get("label", c["id"].replace("_", " ").title())}
                    for c in cfg.get("criteria", [])]
        except Exception:
            pass
    return []


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())

        elif parsed.path == "/api/experiments":
            exps = discover_experiments()
            payload = [{"id": e["id"], "name": e["name"], "description": e["description"]}
                       for e in exps]
            self._json(payload)

        elif parsed.path == "/api/data":
            exp_id = qs.get("experiment", [None])[0]
            if not exp_id:
                self._json({"error": "missing experiment param"}, 400)
                return

            data_dir = EXPERIMENTS_DIR / exp_id / "data"
            runs = []
            if (data_dir / "results.jsonl").exists():
                for line in (data_dir / "results.jsonl").read_text().strip().split("\n"):
                    if line.strip():
                        try:
                            runs.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass

            best_prompt = ""
            if (data_dir / "best_prompt.txt").exists():
                best_prompt = (data_dir / "best_prompt.txt").read_text().strip()

            criteria = get_criteria_meta(exp_id)
            # Fallback: infer criteria keys from first result
            if not criteria and runs:
                criteria = [{"id": k, "label": k.replace("_", " ").title()}
                            for k in (runs[0].get("criteria") or {}).keys()]

            self._json({"runs": runs, "best_prompt": best_prompt, "criteria": criteria})
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # suppress request logs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Autoimprove multi-experiment dashboard")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()

    exps = discover_experiments()
    print(f"Dashboard at http://localhost:{args.port}")
    print(f"Experiments found: {[e['id'] for e in exps] or 'none'}")
    server = HTTPServer(("0.0.0.0", args.port), DashboardHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown.")


if __name__ == "__main__":
    main()
