
async function launchJob({ functionName, params, image, module }) {

  const namespace = 'orpheus';

  const uuidModule = await import('uuid');
  const uuidv4 = uuidModule.v4;
  
  const k8sModule = await import('@kubernetes/client-node');
  const KubeConfig = k8sModule.KubeConfig || k8sModule.default?.KubeConfig;
  const BatchV1Api = k8sModule.BatchV1Api || k8sModule.default?.BatchV1Api;

  const kc = new KubeConfig();
  kc.loadFromFile('/home/r/Workspace/Kubernetes/KuboConfig/config');
  const batchApi = kc.makeApiClient(BatchV1Api);

  const jobName = `job-${functionName.toLowerCase().replace(/[^a-z0-9-]/g, '')}-${uuidv4().slice(0, 5)}`;
  const argsStr = Object.entries(params)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ');
  const execCode = `from ${module} import ${functionName}; ${functionName}(${argsStr})`;

  const job = {
    apiVersion: 'batch/v1',
    kind: 'Job',
    metadata: { name: jobName },
    spec: {
      template: {
        metadata: { labels: { job: jobName } },
        spec: {
          containers: [
            {
              name: 'runner',
              image: image,
              imagePullPolicy: 'Always', // <--- This line makes sure it always pulls the image!
              env: [{ name: 'EXEC_CODE', value: execCode }]
            }
          ],
          restartPolicy: 'Never'
        }
      },
      backoffLimit: 0
    }
};


  try {
    const response = await batchApi.createNamespacedJob({ namespace, body: job });
    const jobInfo = {
      Name: response.metadata?.name,
      Namespace: response.metadata?.namespace,
      Image: response.spec?.template?.spec?.containers?.[0]?.image,
      ImagePullPolicy: response.spec?.template?.spec?.containers?.[0]?.imagePullPolicy,
      Code: (response.spec?.template?.spec?.containers?.[0]?.env || [])
        .find(e => e.name === "EXEC_CODE")?.value,
      Created: response.metadata?.creationTimestamp,
    };

    console.log("✅ Kubernetes Job Launched:");
    Object.entries(jobInfo).forEach(([k, v]) =>
      console.log(`   ${k}: ${v}`)
    );
    return response;
  } catch (err) {
    console.error('❌ K8s API Error (Full):', JSON.stringify(err, null, 2));
    throw new Error(err?.response?.body?.message || err.message || 'Unknown error from Kubernetes');
  }
}
module.exports = { launchJob };

