const express = require('express');
const router = express.Router();
const { launchJob } = require('../kube/jobRunner');
const NAMESPACE = 'orpheus';

async function getK8sClientModules() {
  const k8sModule = await import('@kubernetes/client-node');
  return {
    KubeConfig: k8sModule.KubeConfig,
    BatchV1Api: k8sModule.BatchV1Api,
  };
}


router.post('/run-job', async (req, res) => {
  const { function: functionName, params, image, module } = req.body;

  if (!functionName || typeof params !== 'object' || !image || !module) {
    return res.status(400).json({ error: 'Missing required fields: function, params, image, or module' });
  }

  try {
    const job = await launchJob({ functionName, params, image, module });
    const jobName = job?.metadata?.name;

    if (!jobName) {
      return res.status(500).json({
        error: 'Job launched but response missing metadata.name', details: job});
    }

    res.json({ status: 'Job launched', jobName }, job);
  } catch (err) {
    res.status(500).json({ error: 'Job failed to launch', details: err?.message || err });
  }
});


// ➕ Create a namespaced CronJob
router.post('/cronjobs/create', async (req, res) => {
  const { cronJobManifest } = req.body;

  if (!cronJobManifest || !cronJobManifest.metadata?.name) {
    return res.status(400).json({ error: 'Missing valid cronJobManifest with metadata.name' });
  }

  try {
    const { KubeConfig, BatchV1Api } = await getK8sClientModules();
    const kc = new KubeConfig();
    kc.loadFromFile(process.env.KUBECONFIG);
    const batch = kc.makeApiClient(BatchV1Api);

    const result = await batch.createNamespacedCronJob({ namespace: NAMESPACE, body: cronJobManifest });
    res.status(201).json({ status: 'CronJob created', cronjob: result.body });
  } catch (err) {
    console.error('❌ Failed to create cronjob:', err);
    res.status(500).json({ error: 'Failed to create cronjob', details: err?.message });
  }
});

module.exports = router;

