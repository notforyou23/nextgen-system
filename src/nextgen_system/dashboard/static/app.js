async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}`);
  return res.json();
}

function renderTaskRuns(container, runs) {
  if (!runs.length) {
    container.innerHTML = '<p>No task runs available.</p>';
    return;
  }
  const rows = runs
    .map(
      (run) => `
        <tr>
          <td>${run.task_name}</td>
          <td><span class="status-pill ${run.status}">${run.status}</span></td>
          <td>${run.triggered_at ?? ''}</td>
          <td>${run.completed_at ?? ''}</td>
          <td>${run.error ?? ''}</td>
        </tr>`
    )
    .join('');
  container.innerHTML = `
    <table>
      <thead>
        <tr><th>Task</th><th>Status</th><th>Triggered</th><th>Completed</th><th>Error</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderMetrics(container, metrics) {
  if (!metrics.length) {
    container.innerHTML = '<p>No metrics available.</p>';
    return;
  }
  const rows = metrics
    .map(
      (metric) => `
        <tr>
          <td>${metric.as_of}</td>
          <td>${metric.metric_name}</td>
          <td>${metric.metric_value.toFixed(3)}</td>
          <td>${metric.status}</td>
        </tr>`
    )
    .join('');
  container.innerHTML = `
    <table>
      <thead>
        <tr><th>Date</th><th>Metric</th><th>Value</th><th>Status</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderPredictions(container, predictions) {
  if (!predictions.length) {
    container.innerHTML = '<p>No predictions available.</p>';
    return;
  }
  const rows = predictions
    .map(
      (pred) => `
        <tr>
          <td>${pred.ticker}</td>
          <td>${pred.prediction}</td>
          <td>${pred.probability.toFixed(3)}</td>
          <td>${pred.confidence.toFixed(3)}</td>
          <td>${pred.created_at ?? ''}</td>
        </tr>`
    )
    .join('');
  container.innerHTML = `
    <table>
      <thead>
        <tr><th>Ticker</th><th>Direction</th><th>Probability</th><th>Confidence</th><th>Created</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderTrades(container, trades) {
  if (!trades.length) {
    container.innerHTML = '<p>No trades executed.</p>';
    return;
  }
  const rows = trades
    .map(
      (trade) => `
        <tr>
          <td>${trade.ticker}</td>
          <td>${trade.action}</td>
          <td>${trade.quantity.toFixed(4)}</td>
          <td>${trade.price.toFixed(2)}</td>
          <td>${trade.executed_at ?? ''}</td>
          <td>${trade.status}</td>
        </tr>`
    )
    .join('');
  container.innerHTML = `
    <table>
      <thead>
        <tr><th>Ticker</th><th>Action</th><th>Qty</th><th>Price</th><th>Executed</th><th>Status</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function renderPortfolio(container, snapshot) {
  if (!snapshot) {
    container.innerHTML = '<p>No portfolio snapshot.</p>';
    return;
  }
  container.innerHTML = `
    <p>Total Value: $${snapshot.total_value.toFixed(2)}</p>
    <p>Cash Balance: $${snapshot.cash_balance.toFixed(2)}</p>
    <p>Daily P&L: $${snapshot.pnl_daily.toFixed(2)}</p>
    <p>Total P&L: $${snapshot.pnl_total.toFixed(2)}</p>
    <p>Win Rate: ${(snapshot.win_rate * 100).toFixed(1)}%</p>
  `;
}

async function loadDashboard() {
  try {
    const statusData = await fetchJSON('/status');
    renderTaskRuns(document.getElementById('status'), statusData.task_runs);
    renderMetrics(document.getElementById('feedback'), statusData.feedback_metrics);

    const predictionsData = await fetchJSON('/predictions');
    renderPredictions(document.getElementById('predictions'), predictionsData.predictions);

    const tradesData = await fetchJSON('/trades');
    renderTrades(document.getElementById('trades'), tradesData.trades);

    const portfolioData = await fetchJSON('/portfolio');
    renderPortfolio(document.getElementById('portfolio'), portfolioData.portfolio);
  } catch (err) {
    console.error(err);
    alert('Failed to load dashboard data. Check console for details.');
  }
}

document.getElementById('refresh').addEventListener('click', loadDashboard);
loadDashboard();
