const express = require('express');
const path = require('path');
const livereload = require('livereload');
const connectLivereload = require('connect-livereload');
const { launchJob } = import('./kube/jobRunner.js');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3000;

const liveReloadServer = livereload.createServer();
liveReloadServer.watch(path.join(__dirname, 'public'));

// 📡 Inject livereload script into served HTML
app.use(connectLivereload());

// 🔧 Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// 🧠 Reload browser when file changes are detected
liveReloadServer.server.once('connection', () => {
  setTimeout(() => {
    liveReloadServer.refresh('/');
  }, 100);
});



// Default route
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});


app.use(bodyParser.json());
app.post('/charts', async (req, res) => {
  const { function: functionName, params } = req.body;

  if (!functionName || typeof params !== 'object') {
    return res.status(400).json({ error: 'Missing function name or parameters' });
  }

  try {
    const job = await launchJob(functionName, params);
    res.json({ status: 'Job launched', jobName: job.metadata.name });
  } catch (err) {
    console.error('Failed to launch job:', err);
    res.status(500).json({ error: 'Job failed to launch' });
  }
});



app.listen(PORT, () => {
  console.log(`🚀 Dashboard running at http://localhost:${PORT}`);
});
