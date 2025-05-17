const { v4: uuidv4 } = require('uuid');

async function launchJob(functionName, params) {
  const k8s = await import('@kubernetes/client-node');
  const kc = new k8s.default.KubeConfig(); // Note: Use `.default`
  kc.loadFromDefault();
  const batchApi = kc.makeApiClient(k8s.default.BatchV1Api);

  const jobName = `chart-job-${functionName}-${uuidv4().slice(0, 5)}`;
  const argsStr = Object.entries(params)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ');
  const code = `from app import charts; charts.${functionName}(${argsStr})`;

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
              name: 'chart-runner',
              image: 'thales884/charts:latest',
              env: [{ name: 'EXEC_CODE', value: code }]
            }
          ],
          restartPolicy: 'Never'
        }
      },
      backoffLimit: 0
    }
  };

  const res = await batchApi.createNamespacedJob('default', job);
  return res.body;
}

module.exports = { launchJob };
