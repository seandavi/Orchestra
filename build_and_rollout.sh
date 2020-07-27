#!/usr/bin/env bash
set -euo pipefail

docker build -t seandavi/workshop-orchestra .
docker push seandavi/workshop-orchestra
kubectl rollout restart deployment/workshop-orchestra
