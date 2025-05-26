 window.notification = function (message, level = 'info', sticky = false) {
    const levels = {
      success: '#22c55e',   // green
      info: '#9ca3af',      // gray
      error: '#ef4444'      // red
    };

    const bgColor = levels[level] || levels.info;
    const notification = document.createElement('div');
    notification.style = `
      background-color: ${bgColor};
      color: white;
      padding: 0.75rem 1rem;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      font-size: 0.875rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      min-width: 240px;
      max-width: 360px;
    `;
    
    notification.innerHTML = `
      <span>${message}</span>
      <button onclick="this.parentElement.remove()" style="margin-left: 1rem; background: none; color: white; border: none; cursor: pointer; font-weight: bold;">✕</button>
    `;

    document.getElementById('notification-container').appendChild(notification);

    if (!sticky) {
      setTimeout(() => {
        notification.remove();
      }, 5000);
    }
  };

window.launchJobUI = function () {
  const functionName = document.getElementById('function-select').value;
  const ticker = document.getElementById('input-ticker').value;
  const start = document.getElementById('input-start').value;
  const end = document.getElementById('input-end').value;
  const interval = document.getElementById('input-interval').value;

  const formatDate = dateStr => parseInt(dateStr.replaceAll('-', ''), 10);

  const params = {
    ticker,
    start_date: formatDate(start),
    end_date: formatDate(end),
    interval: parseInt(interval, 10)
  };

  const payload = {
    function: functionName,
    params,
    image: 'thales884/charts:latest',
    module: 'main',
    
  };

  console.log('Launching job with parameters:', payload);

  fetch('/run-job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(res => res.json())
    .then(data => {
      if (data.jobName) {
        notification(`✅ Job launched: ${data.jobName}`, 'success');
      } else if (data.error) {
        notification(`❌ Failed to launch job: ${data.error}`, 'error', true);
      } else {
        notification('⚠️ Unknown response from server', 'info');
      }
    })
    .catch(err => {
      notification(`❌ Error launching job: ${err.message || err}`, 'error', true);
    });
};


// window.checkDatabaseStatus = function () {
//   const endpoints = ['options', 'stocks', 'users'];
//   endpoints.forEach(id => {
//     fetch(`/db/check?target=${id}`)
//       .then(res => res.json())
//       .then(data => {
//         const dot = document.querySelector(`#status-${id} div`);
//         if (data.status !== 'success') {
//           dot.style.backgroundColor = '#f97316';
//         }
//       })
//       .catch(() => {
//         const dot = document.querySelector(`#status-${id} div`);
//         dot.style.backgroundColor = '#f97316';
//       });
//   });
// };

// document.addEventListener('DOMContentLoaded', () => {
//   checkDatabaseStatus();
//   loadModule('workloads', 'workload-module');
//   loadModule('logs', 'logs-module');
// });


window.loadK8sMetrics = async function () {
  const container = document.getElementById('k8s-metrics-content');
  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
      <h3 style="margin: 0;">Kubernetes Workloads</h3>
      <button onclick="loadK8sMetrics()" style="background: #0ea5e9; color: white; border: none; padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer;">Refresh</button>
    </div>
    <p>Loading Kubernetes workloads...</p>`;

  try {
    const jobsRes = await fetch('/k8s/jobs');
    const jobs = await jobsRes.json();

    const jobCards = jobs.map(job => {
      const status = job.completions
        ? '✅'
        : job.failed
        ? '❌'
        : '⏳';

      return `
        <div 
          class="job-line" 
          data-job-name="${job.name}" 
          onclick="toggleJobSelection(this)"
          style="cursor: pointer; display: flex; align-items: center; justify-content: space-between; padding: 0.5rem 1rem; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb;">
          <span style="color: #0ea5e9; font-weight: 500;">${job.name}</span>
          <span>${status}</span>
        </div>
        <div class="job-details" style="display: none; background: #fff; margin-top: 0.25rem; padding: 0.5rem 1rem; border-left: 2px solid #0ea5e9; border-radius: 0 0 8px 8px;">
          <p><strong>Started:</strong> ${new Date(job.startTime).toLocaleString()}</p>
          <p><strong>Completions:</strong> ${job.completions} | <strong>Failed:</strong> ${job.failed}</p>
          <details>
            <summary style="cursor: pointer;">Conditions</summary>
            <ul style="padding-left: 1rem;">
              ${job.conditions?.map(cond => `
                <li><strong>${cond.type}:</strong> ${cond.reason} — ${cond.message}</li>
              `).join('') || "<li><em>No conditions reported</em></li>"}
            </ul>
          </details>
          <button onclick="loadLogs('${job.name}', this)" style="margin-top: 0.5rem; background: #111827; color: white; padding: 0.25rem 0.75rem; border: none; border-radius: 6px;">View Logs</button>
          <pre class="job-log" style="display:none; background:#000; color:#0f0; padding:0.5rem; margin-top:0.5rem; max-height:200px; overflow-y:auto;"></pre>
        </div>
      `;
    });

    container.innerHTML = jobCards.join('');
  } catch (err) {
    container.innerHTML = `<p style="color: red;">Failed to load workloads: ${err.message}</p>`;
    console.error('❌ Workload load error:', err);
  }
};

function toggleJobSelection(element) {
  document.querySelectorAll('.job-details').forEach(el => el.style.display = 'none');
  const details = element.nextElementSibling;
  if (details.style.display === 'none') {
    details.style.display = 'block';
  } else {
    details.style.display = 'none';
  }
}

async function loadLogs(jobName, btn) {
  const logs = btn.parentElement.querySelector('.job-log');
  document.querySelectorAll('.job-log').forEach(log => log.style.display = 'none');
  logs.style.display = 'block';
  logs.textContent = 'Loading logs...';

  try {
    const res = await fetch('/k8s/pods/logs', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ jobName })
    });

    if (!res.ok) throw new Error(await res.text());

    const data = await res.text();
    logs.textContent = data;
  } catch (err) {
    logs.textContent = '❌ Failed to load logs: ' + err.message;
  }
} 

// Highlight selection logic
window.toggleJobSelection = function (element) {
  const isSelected = element.classList.contains('selected');
  element.classList.toggle('selected', !isSelected);
  element.style.backgroundColor = isSelected ? '#f9fafb' : '#dbeafe'; // default vs selected
  element.style.borderColor = isSelected ? '#e5e7eb' : '#3b82f6';

  const detail = element.nextElementSibling;
  if (detail && detail.classList.contains('job-details')) {
    detail.style.display = isSelected ? 'none' : 'block';
  }
};


function getSelectedJobNames() {
  return Array.from(document.querySelectorAll('.job-line.selected'))
    .map(el => el.dataset.jobName);
}

window.bulkDeleteWorkloads = async function () {
  const jobNames = getSelectedJobNames();
  for (const name of jobNames) {
    try {
      const res = await fetch(`/k8s/jobs/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      const data = await res.json();
      notification(`🗑 Job deleted: ${data.job}`, 'success');
    } catch (err) {
      console.error(`❌ Could not delete ${name}:`, err);
      notification(`❌ Failed to delete job: ${name}`, 'error', true);
    }
  }
  loadK8sMetrics();
};


window.bulkStartWorkloads = async function () {
  const jobNames = getSelectedJobNames();
  for (const name of jobNames) {
    try {
      const res = await fetch(`/k8s/jobs/restart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      const json = await res.json();
      console.log(`▶ Restarted ${name}:`, json);
    } catch (err) {
      console.error(`❌ Could not restart ${name}:`, err);
    }
  }
  loadK8sMetrics();
};

window.bulkLogsWorkloads = async function () {
  const jobNames = getSelectedJobNames();
  const logBox = document.getElementById('logs-module');
  logBox.innerHTML = ''; // clear previous logs

  for (const name of jobNames) {
    try {
      const res = await fetch(`/k8s/pods/${name}/logs`);
      const text = await res.text();

      const pre = document.createElement('pre');
      pre.textContent = `📄 Logs for ${name}:\n\n${text}`;
      pre.style = 'background: #f3f4f6; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;';
      logBox.appendChild(pre);
    } catch (err) {
      console.error(`❌ Could not get logs for ${name}:`, err);
    }
  }
};



// Main dashboard loader
window.loadDbDashboard = function () {
  refreshDbSummary();
  refreshDbLiveMetrics();
  refreshTickersTable();
};

// Summary: tables, sizes, contract/quote counts
window.refreshDbSummary = async function () {
  const target = document.getElementById('db-summary-content');
  if (!target) return;
  target.innerHTML = `<div class="desc-text">Loading database summary...</div>`;
  try {
    const res = await fetch('/db/summary');
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    target.innerHTML = `
      <div class="flex-row" style="gap:2rem;flex-wrap:wrap;">
        <div class="stat-card">Tables<br><span>${data.total_tables}</span></div>
        <div class="stat-card">DB Size<br><span>${formatBytes(data.total_db_size_bytes)}</span></div>
        <div class="stat-card">Contracts<br><span>${data.contract_count}</span></div>
        <div class="stat-card">Quotes<br><span>${data.quote_count}</span></div>
      </div>
      <h4 style="margin-top:1.2em;">Largest Tables</h4>
      <table class="pretty-table" style="margin-bottom:0.7em;">
        <thead><tr><th>Table</th><th>Size</th></tr></thead>
        <tbody>
          ${data.largest_tables.map(t => `<tr><td>${t.table}</td><td>${formatBytes(t.size_bytes)}</td></tr>`).join('')}
        </tbody>
      </table>
      <div class="desc-text">Last updated: ${new Date(data.updated_at).toLocaleString()}</div>
    `;
  } catch (e) {
    target.innerHTML = `<span class="badge badge-danger">Error loading summary: ${e.message}</span>`;
    if (window.notification) window.notification('Error loading DB summary', 'error');
  }
};

// Live status: connections, latency, QPS, inserts/sec, selects/sec
// Format uptime as "1d 2h 12m"
function formatUptime(seconds) {
  if (isNaN(seconds)) return '-';
  const d = Math.floor(seconds / 86400);
  seconds %= 86400;
  const h = Math.floor(seconds / 3600);
  seconds %= 3600;
  const m = Math.floor(seconds / 60);
  seconds = Math.floor(seconds % 60);
  return [
    d ? `${d}d` : '',
    h ? `${h}h` : '',
    m ? `${m}m` : '',
    seconds ? `${seconds}s` : ''
  ].filter(Boolean).join(' ');
}

window.refreshDbLiveMetrics = async function () {
  console.log('Running refreshDbLiveMetrics...');
  let meta = null, live = null;

  // Metadata
  try {
    const resMeta = await fetch('/db/metadata');
    if (!resMeta.ok) throw new Error(await resMeta.text());
    meta = await resMeta.json();
    console.log('DB Metadata:', meta);
  } catch (e) {
    meta = null;
    console.error('Error loading DB metadata', e);
    if (window.notification) window.notification('Error loading DB metadata', 'error');
  }

  // Live status
  try {
    const resLive = await fetch('/db/live-status');
    if (!resLive.ok) throw new Error(await resLive.text());
    live = await resLive.json();
    console.log('DB Live Status:', live);

  } catch (e) {
    live = null;
    console.error('Error loading DB live status', e);
    if (window.notification) window.notification('Error loading DB live status', 'error');
  }

  // Status badge
  try {
    let statusText = (meta && meta.status) ? meta.status : 'unknown';
    statusText = statusText.charAt(0).toUpperCase() + statusText.slice(1);

    // Table status
    const badgeTable = document.getElementById('metric-status').querySelector('.badge');
    badgeTable.textContent = statusText;
    badgeTable.className = 'badge ' + (statusText === 'Healthy' ? 'badge-success' : 'badge-danger');

    // Disk usage
    document.getElementById('disk-usage-label').textContent =
      (meta && meta.size_pretty) ? meta.size_pretty : '-';

    // Connections
    // Assume 'live' object returned from /db/live-status
    document.getElementById('connections-value').textContent =
      (live && typeof live.connections !== 'undefined') ? live.connections : '-';

    document.getElementById('latency-value').textContent =
      (live && typeof live.latency_ms !== 'undefined') ? live.latency_ms : '-';

    document.getElementById('inserts-value').textContent =
      (live && typeof live.inserts_per_sec !== 'undefined') ? live.inserts_per_sec : '-';

    document.getElementById('selects-value').textContent =
      (live && typeof live.selects_per_sec !== 'undefined') ? live.selects_per_sec : '-';

    document.getElementById('bandwidth-value').textContent =
      (live && typeof live.bandwidth_in !== 'undefined' && typeof live.bandwidth_out !== 'undefined')
        ? `${live.bandwidth_in} / ${live.bandwidth_out}` : '-';

    document.getElementById('qps-value').textContent =
      (live && typeof live.qps !== 'undefined') ? live.qps : '-';

    // Uptime
    document.getElementById('metric-uptime').textContent =
      (meta && typeof meta.uptime_seconds !== 'undefined') ? formatUptime(meta.uptime_seconds) : '-';

    // Bandwidth (if not available, skip)
    document.getElementById('bandwidth-value').textContent = '-';
  } catch (e) {
    console.error('Error updating metric elements:', e);
  }
};




// Ticker table
window.refreshTickersTable = async function () {
  const body = document.getElementById('tickers-table-body');
  if (!body) return;
  body.innerHTML = `<tr><td colspan="5" class="desc-text">Loading tickers...</td></tr>`;
  try {
    const res = await fetch('/db/ticker-summary');
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const allTickers = data.tickers || [];
    body.innerHTML = allTickers.length === 0
      ? `<tr><td colspan="5" class="desc-text">No tickers found.</td></tr>`
      : allTickers.map(t =>
        `<tr>
          <td>${t.ticker}</td>
          <td>${t.contract_count}</td>
          <td>${t.expiration_count}</td>
          <td>${t.earliest_expiration || '-'}</td>
          <td>${t.latest_expiration || '-'}</td>
        </tr>`
      ).join('');
  } catch (e) {
    body.innerHTML = `<tr><td colspan="5" class="badge badge-danger">Error loading tickers</td></tr>`;
    if (window.notification) window.notification('Error loading tickers', 'error');
  }
};

// Polling
function setDbMetricsPollInterval(ms) {
  dbMetricsPollInterval = parseInt(ms, 10);
  if (dbMetricsPollTimer) clearInterval(dbMetricsPollTimer);
  dbMetricsPollTimer = setInterval(() => {
    refreshDbSummary();
    refreshDbLiveStatus();
    refreshDbUptime();
    refreshTickersTable();
  }, dbMetricsPollInterval);
}

// Helpers
function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatUptime(seconds) {
  if (isNaN(seconds)) return '-';
  const days = Math.floor(seconds / 86400);
  seconds %= 86400;
  const hours = Math.floor(seconds / 3600);
  seconds %= 3600;
  const minutes = Math.floor(seconds / 60);
  seconds = Math.floor(seconds % 60);
  return [
    days ? `${days}d` : '',
    hours ? `${hours}h` : '',
    minutes ? `${minutes}m` : '',
    seconds ? `${seconds}s` : ''
  ].filter(Boolean).join(' ');
}

// Modal (optional, can be customized)
function showMetricDetail(metric) {
  const modal = document.getElementById('metric-details-modal');
  modal.style.display = 'flex';
  modal.innerHTML = `
    <div class="dashboard-square" style="max-width:580px;margin:auto;">
      <h3>${metric === 'all' ? 'All Database Metrics (24h)' : 'Metric: ' + metric}</h3>
      <div id="metric-details-content" style="min-height:120px;"></div>
      <button class="refresh-btn" onclick="closeMetricModal()" style="margin-top:1em;">Close</button>
    </div>`;
  // You can fetch historical/advanced metrics here if needed.
}
window.closeMetricModal = () => {
  document.getElementById('metric-details-modal').style.display = 'none';
};

// Init
document.addEventListener('DOMContentLoaded', () => {
  refreshDbSummary();
  refreshDbLiveStatus();
  refreshDbUptime();
  refreshTickersTable();
  setDbMetricsPollInterval(dbMetricsPollInterval);
});
