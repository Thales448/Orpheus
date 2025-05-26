

window.loadTab = function(tabName) {
  const contentEl = document.getElementById('main-content');
  if (tabName === 'databases') {
  if (window.refreshDbLiveMetrics) setTimeout(window.refreshDbLiveMetrics, 50);
}

  // Special-case: use a JS dashboard for 'databases'
  // if (tabName === 'databases') {
  //   // Clear content first, then render dashboard
  //   contentEl.innerHTML = '';
  //   loadDbDashboard(contentEl); // pass the main container
  //   return;
  // }
  // Add more tab modules here if desired:
  // if (tabName === 'algorithms') { loadAlgorithmsDashboard(contentEl); return; }

  // Default: load an HTML fragment
  fetch(`${tabName}.html`)
    .then(response => {
      if (!response.ok) throw new Error('Failed to load tab: ' + tabName);
      return response.text();
    })
    .then(html => {
      contentEl.innerHTML = html;
    })
    .catch(err => {
      contentEl.innerHTML = `<p style="color:red">Error loading content for ${tabName}.</p>`;
      console.error(err);
    });
}
