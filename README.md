# Spark at Scale

With this project, we aim to identify the relationship between memory parameters in a Spark-on-Kubernetes environment and executor/task failure. Specifically, we suspect that there's a relationship among executor memory allocation, table size (relative to the executor memory allocation), and the join strategy being used. Within the table sizes, there are also variables like data asymmetry and skew that we suspect could cause executor and task failure.

Most of the stuff below is like a runbook as we conduct our research. To see a polished paper with our specific evaluation and methodology, read the paper (coming soon!).

# Configuring the Testbed

1. Use your cloud provider of choice to create a Kubernetes cluster. Configure it to be what `kubectl` talks to. If you use GCP, consider the following:

```
gcloud container clusters get-credentials <cluster_name> --zone <zone> --project <project>
```

You can check that you're talking to the right cluster with:

```
kubectl config current-context
```

2. We'll be using the Spark on Kubernetes operator. But first, we'll need to put together some objects. We'll run the operator in its own namespace (the release `sparkoperator` in the NS `spark-operator`), and we'll run the actual spark jobs in another namespace (NS `spark-apps`). We'll also need to configure a ServiceAccount (called `spark`) to the `spark-apps` namespace, as well as a ClusterRoleBinding to associate that ServiceAccount with a cluster-level role.

To do all of this, simply run `kubectl apply -f config/spark-operator.yaml`.

3. Now, we have to install the operator, which will create an Operator that will run in the `spark-operator` namespace in its own Pod.

```bash
# Pull a "reference" to the operator itself
helm repo add spark-operator https://googlecloudplatform.github.io/spark-on-k8s-operator

# Install it!
# "sparkoperator" is the name of the release. We install it into the spark-operator namespace.
# We set that the namespace in which spark *jobs* run is spark-apps.
helm install sparkoperator spark-operator/spark-operator --namespace spark-operator --set sparkJobNamespace=spark-apps,enableWebhook=true
```

I actually ran into an issue where the operator was unable to pull an image from GCR. I was able to find this out because when I did `k get pods --all-namespaces`, I saw that the pod for the operator had status of ImagePullBackoff. I fixed this by changing the image for the deployment to be a spark operator image on a GCR instance within the same project as my GKE cluster (I pulled the [image](gcr.io/spark-operator/spark-operator:v1beta2-1.3.0-3.1.1) from GCR locally, tagged it, and re-pushed it to my own GCR instance).

Fix:

```bash
# Get the deployment
kubectl get deployments -n spark-operator

# Modify the image URL
kubectl edit deployment <deployment_name> -n spark-operator

# Restart the deployment
kubectl rollout restart deployments/<deployment_name> -n spark-operator
```

4. Submit an example job to spark! If you have a YAML file for a SparkApplication, you can apply it to the cluster. For example, let's say that you want to run the example Pi approximation job in `examples/spark-pi.yaml`. You'd do:

```
kubectl apply -f examples/spark-pi.yaml
```

If all is going well, that should spin up a driver pod. Here are some useful commands you can use to check that all is going well (for the above example):

```bash
# See metadata and *events* (not logs) for the spark-pi SparkApplication that was created
kubectl describe SparkApplication spark-pi -n spark-apps

# Seeing the SparkApplication is great, but what if you want to find the pod logs?
# First find the pod:
kubectl get pods -n spark-apps

# Then, using that pod, get the logs for it:
kubectl logs -f <pod_name> -n spark-apps
```

You should see "Pi is roughly 3.14" in those logs!

5. Getting the spark traces would be very useful. We can enable this with `.spec.sparkConf.spark.eventLog.enabled`, and we can set a path to log with `.spec.sparkConf.spark.eventLog.dir`. But since we run in pods, the directory won't be as simple as just `/tmp/spark-events/`. How do we resolve this?

Instead of using `/tmp/spark-events/`, we use some Cloud Storage from Google. So we can do something like: `'spark.eventLog.dir': 'gs://spark-log-bucket/spark-events/'`.

6. Accessing the UI while a job runs. Unclear how to get this to work, so we'll leave this as a TODO.

7. Run your own jobs. For this, you'll need to write a query, Dockerize it, push the image to a private repository, and then create a job configuration file for it (in `benchmarks/`) and apply it using the steps in step 4.

Right now, this is sort of working. You can create an image of `src/` using the following:

```
docker build -f Dockerfile -t gcr.io/neeva-spark/<name> .
```

And then you can push it to GCR:

```
docker push gcr.io/neeva-spark/<name>
```

And then you can take the image URL from GCR and put it into a YAML configuration file, like `spark-pi.yaml`.

# Running Custom Jobs

1. Write the job in `benchmarks/` as something like `job.scala`
2. Create a Docker image for it (using the provided `Dockerfile` in `benchmarks/`, which is a TODO)
3. Tag the Docker image, push it to your private GCR instance
4. Create a resource definition for it using the template in `benchmarks/` (TODO)
5. Pull the logs (figuring this out is a TODO) so that you can analyze the locally

# Sources

1. Most of the configuration steps came directly from here, since the official docs didn't work out too well: https://dzlab.github.io/ml/2020/07/14/spark-kubernetes/.
2. The operator's repository has the original source for the examples contained in `examples/`.
