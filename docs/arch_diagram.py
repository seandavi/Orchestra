#!/usr/bin/env python3

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.network import Route53
from diagrams.onprem.database import Postgresql
from diagrams.gcp.network import LoadBalancing
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.client import Users, Client
from diagrams.k8s.compute import Pod
from diagrams.k8s.infra import Master
from diagrams.k8s.controlplane import API
from diagrams.k8s.network import Ingress, Service
from diagrams.onprem.network import Traefik
from diagrams.programming.language import Python

with Diagram("Simplified Orchestra Architecture Diagram", show=False):
    dns = Route53("Wildcard DNS\n*.bioc.cancerdatasci.org")
    lb = LoadBalancing("Load Balancer")
    pg = Postgresql("AWS Aurora PostgreSQL")
    users = Users("Workshop\nParticipants")
    web = Client("Standard Web Browser")
    with Cluster("Kubernetes Cluster"):
        app = Python("Orchestra")
        master = Master("Kubernetes Master\nRunning on GKE")
        k8api = API("Kubernetes Control API")
        s = []
        w = []
        ing = Traefik("Router & Proxy")
        ing >> app
        app >> pg
        app >> k8api
        k8api >> master
        pg >> app
        prom = Prometheus("Prometheus\nMonitoring")
        graf = Grafana("Grafana\nVisualization")
        ing >> graf
        graf >> prom
        for i in range(0, 5):
            with Cluster(f"Workshop {i+1}"):
                s.append(Service(f"Service"))
                w.append(Pod(f"Rstudio"))
                s[i] >> w[i]
                ing >> s[i]
                master - Edge(color="firebrick", style="dashed") - s[i]
                master - Edge(color="firebrick", style="dashed") - w[i]
            prom >> w[i]

    lb >> ing
    master  - Edge(color="firebrick", style="dashed") - ing
    users >> web
    dns >> web
    web >> dns
    web >> lb
