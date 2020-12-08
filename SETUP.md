# Setup

## Cluster

1. Setup cluster

```bash
gcloud beta container --project "nih-strides-orchestra" clusters create "orchestra" --zone "us-central1-c" --no-enable-basic-auth --cluster-version "1.17.13-gke.2001" --release-channel "regular" --machine-type "e2-medium" --image-type "COS" --disk-type "pd-standard" --disk-size "100" --metadata disable-legacy-endpoints=true --scopes "https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --num-nodes "3" --enable-stackdriver-kubernetes --enable-ip-alias --network "projects/nih-strides-orchestra/global/networks/default" --subnetwork "projects/nih-strides-orchestra/regions/us-central1/subnetworks/default" --default-max-pods-per-node "110" --no-enable-master-authorized-networks --addons HorizontalPodAutoscaling,HttpLoadBalancing --enable-autoupgrade --enable-autorepair --max-surge-upgrade 1 --max-unavailable-upgrade 0 --labels project=orchestra && gcloud beta container --project "nih-strides-orchestra" node-pools create "pool-1" --cluster "orchestra" --zone "us-central1-c" --machine-type "e2-highmem-4" --image-type "COS" --disk-type "pd-standard" --disk-size "200" --metadata disable-legacy-endpoints=true --scopes "https://www.googleapis.com/auth/devstorage.read_only","https://www.googleapis.com/auth/logging.write","https://www.googleapis.com/auth/monitoring","https://www.googleapis.com/auth/servicecontrol","https://www.googleapis.com/auth/service.management.readonly","https://www.googleapis.com/auth/trace.append" --num-nodes "3" --enable-autoscaling --min-nodes "0" --max-nodes "20" --enable-autoupgrade --enable-autorepair --max-surge-upgrade 1 --max-unavailable-upgrade 0
```

2. setup kubectl

```bash
gcloud container clusters get-credentials --zone=us-central1-c orchestra
```

3. Install istioctl and Istio

- https://istio.io/latest/docs/setup/install/istioctl/

```
istioctl install --set profile=default
```

Verify the installation:

```bash
kubectl -n istio-system get deploy
```
Should result in:

```
NAME                   READY   UP-TO-DATE   AVAILABLE   AGE
istio-ingressgateway   1/1     1            1           42s
istiod                 1/1     1            1           59s
```

4. Enable sidecar injection

```bash
kubectl label namespace default istio-injection=enabled
```

5. Add environment variables

```bash
dotenv -f .env bash create_secrets.sh
```
