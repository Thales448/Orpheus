const express = require('express');
const router = express.Router();
const NAMESPACE = 'orpheus';


router.use((req, res, next) => {
  console.log(`[K8S ROUTER] ${req.method} ${req.url}`);
  next();
});


// 🛠 Dynamic import of ES module client-node
async function getK8sClientModules() {
  const k8sModule = await import('@kubernetes/client-node');
  return {
    KubeConfig: k8sModule.KubeConfig,
    CoreV1Api: k8sModule.CoreV1Api,
    BatchV1Api: k8sModule.BatchV1Api,
    Log: k8sModule.Log,
  };
}

// 🟢 List pods in namespace
router.get('/pods', async (req, res) => {
  try {
    const { KubeConfig, CoreV1Api } = await getK8sClientModules();
    const kc = new KubeConfig();
    kc.loadFromFile(process.env.KUBECONFIG);
    const core = kc.makeApiClient(CoreV1Api);

    const podsRes = await core.listNamespacedPod({'namespace':'orpheus'});
    const pods = podsRes.items.map(pod => ({
      name: pod.metadata.name,
      phase: pod.status.phase,
      startTime: pod.status.startTime,
      containers: pod.spec.containers.map(c => c.name),
      conditions: pod.status.conditions || []
    }));

    res.json(pods);
  } catch (err) {
    console.error('❌ Error fetching pods:', err);
    res.status(500).json({ error: 'Failed to fetch pods', details: err.message });
  }
});

// 📄 Get logs from a pod
router.post('/pods/logs', async (req, res) => {
  const { jobName } = req.body;
  if (!jobName) {
    return res.status(400).json({ error: 'Missing jobName in request body' });
  }

  try {
    const { KubeConfig, CoreV1Api, Log } = await getK8sClientModules();
    const kc = new KubeConfig();
    kc.loadFromFile(process.env.KUBECONFIG);

    const core = kc.makeApiClient(CoreV1Api);
    const logApi = new Log(kc);

    const podsRes = await core.listNamespacedPod({'namespace':'orpheus'});
    const matchingPod = podsRes.items.find(p =>
      p.metadata?.name?.startsWith(`${jobName}-`)
    );

    if (!matchingPod) {
      return res.status(404).json({ error: `No pod found for job "${jobName}"` });
    }

    const podName = matchingPod.metadata.name;
    const containerName = matchingPod.spec?.containers?.[0]?.name;

    if (!containerName) {
      return res.status(500).json({ error: `Pod "${podName}" has no containers` });
    }

    console.log(`📦 Fetching logs from pod: ${podName}, container: ${containerName}`);

    const logs = await core.readNamespacedPodLog({'name':podName, 'namespace':'orpheus','container': containerName});


    res.send(logs);
  } catch (err) {
    console.error(`❌ Failed to retrieve logs for job "${req.body.jobName}":`, err);
    res.status(500).json({
      error: 'Failed to retrieve logs',
      details: err?.message || 'Unknown error',
    });
  }
});



// 📦 List jobs in namespace
router.get('/jobs', async (req, res) => {
  const { KubeConfig, BatchV1Api } = await getK8sClientModules();
  const kc = new KubeConfig();
  kc.loadFromFile(process.env.KUBECONFIG);
  const batch = kc.makeApiClient(BatchV1Api);
  const { items } = await batch.listNamespacedJob({ namespace: NAMESPACE });

  res.json(items.map(job => ({
    name: job.metadata.name,
    completions: job.status.succeeded || 0,
    failed: job.status.failed || 0,
    active: job.status.active || 0,
    startTime: job.status.startTime,
    conditions: job.status.conditions || [],
  })));
});

router.get('/cronjobs', async (req, res) => {
  const { KubeConfig, BatchV1Api } = await getK8sClientModules();
  const kc = new KubeConfig();
  kc.loadFromFile(process.env.KUBECONFIG);
  const batch = kc.makeApiClient(BatchV1Api);
  const { items } = await batch.listNamespacedCronJob({ namespace: NAMESPACE });

  res.json(items.map(job => ({
    name: job.metadata.name,
    completions: job.status.succeeded || 0,
    failed: job.status.failed || 0,
    active: job.status.active || 0,
    startTime: job.status.startTime,
    conditions: job.status.conditions || [],
  })));
});

// ❌ Delete a job
router.post('/jobs/delete', async (req, res) => {
  const { name } = req.body;
  if (!name) return res.status(400).json({ error: 'Missing job name' });

  const { KubeConfig, BatchV1Api } = await getK8sClientModules();
  const kc = new KubeConfig();
  kc.loadFromFile(process.env.KUBECONFIG);
  const batch = kc.makeApiClient(BatchV1Api);

  try {
    await batch.deleteNamespacedJob({'name':name, 'namespace':NAMESPACE,
      body: {
        propagationPolicy: 'Background'
      }
    });
    res.json({ status: 'deleted', job: name });
  } catch (err) {
    console.error(`❌ Error deleting job ${name}:`, err);
    res.status(500).json({ error: err.message });
  }
});


// 🟢 Kubernetes health check
router.get('/k8s-health', async (req, res) => {
  try {
    const { KubeConfig, CoreV1Api } = await getK8sClientModules();
    const kc = new KubeConfig();
    kc.loadFromFile(process.env.KUBECONFIG);
    const coreApi = kc.makeApiClient(CoreV1Api);

    const { items } = await coreApi.listNamespace();

    if (!items.length) {
      throw new Error("No items returned from Kubernetes API.");
    }

    res.json({
      status: 'connected',
      context: kc.getCurrentContext(),
      namespaces: items.map(n => n.metadata.name)
    });
  } catch (err) {
    console.error('❌ Kubernetes connectivity test failed:', err);
    res.status(500).json({
      error: 'Kubernetes connection failed',
      details: err?.message || err
    });
  }
});

module.exports = router;