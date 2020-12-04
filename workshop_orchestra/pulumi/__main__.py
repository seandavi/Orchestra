"""A Python Pulumi program"""

import pulumi

from pulumi_gcp import storage

# Create a GCP resource (Storage Bucket)
bucket = storage.Bucket('my-bucket-123-123',
    labels={'environment': "dev"})

# Export the DNS name of the bucket
pulumi.export('bucket_name',  bucket.url)

from pulumi import Config, export, get_project, get_stack, Output, ResourceOptions
from pulumi_gcp.config import project, zone
from pulumi_gcp.container import Cluster, ClusterMasterAuthArgs, ClusterNodeConfigArgs
from pulumi_kubernetes import Provider
from pulumi_kubernetes.apps.v1 import Deployment, DeploymentSpecArgs
from pulumi_kubernetes.core.v1 import ContainerArgs, PodSpecArgs, PodTemplateSpecArgs, Service, ServicePortArgs, ServiceSpecArgs
from pulumi_kubernetes.meta.v1 import LabelSelectorArgs, ObjectMetaArgs
from pulumi_kubernetes.rbac.v1 import ClusterRole, ClusterRoleBinding
from pulumi_kubernetes.core.v1 import ServiceAccount
from pulumi_random import RandomPassword
import pulumi_gcp

# Read in some configurable settings for our cluster:
config = Config('.env')

# nodeCount is the number of cluster nodes to provision. Defaults to 3 if unspecified.
NODE_COUNT = config.get_int('node_count') or 3
# nodeMachineType is the machine type to use for cluster nodes. Defaults to n1-standard-1 if unspecified.
# See https://cloud.google.com/compute/docs/machine-types for more details on available machine types.
NODE_MACHINE_TYPE = config.get('node_machine_type') or 'n1-standard-1'
# username is the admin username for the cluster.
USERNAME = config.get('username') or 'admin'
# password is the password for the admin user in the cluster.
PASSWORD = config.get_secret('password') or RandomPassword("password", length=20, special=True).result
# master version of GKE engine
MASTER_VERSION = config.get('master_version')

# Now, actually create the GKE cluster.
k8s_cluster = Cluster('gke-cluster',
    initial_node_count=NODE_COUNT,
    node_version=MASTER_VERSION,
    min_master_version=MASTER_VERSION,
    master_auth=ClusterMasterAuthArgs(username=USERNAME, password=PASSWORD),
    node_config=ClusterNodeConfigArgs(
        machine_type=NODE_MACHINE_TYPE,
        oauth_scopes=[
            'https://www.googleapis.com/auth/compute',
            'https://www.googleapis.com/auth/devstorage.read_only',
            'https://www.googleapis.com/auth/logging.write',
            'https://www.googleapis.com/auth/monitoring'
        ],
    ),
)

# Manufacture a GKE-style Kubeconfig. Note that this is slightly "different" because of the way GKE requires
# gcloud to be in the picture for cluster authentication (rather than using the client cert/key directly).
k8s_info = Output.all(k8s_cluster.name, k8s_cluster.endpoint, k8s_cluster.master_auth)
k8s_config = k8s_info.apply(
    lambda info: """apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {0}
    server: https://{1}
  name: {2}
contexts:
- context:
    cluster: {2}
    user: {2}
  name: {2}
current-context: {2}
kind: Config
preferences: {{}}
users:
- name: {2}
  user:
    auth-provider:
      config:
        cmd-args: config config-helper --format=json
        cmd-path: gcloud
        expiry-key: '{{.credential.token_expiry}}'
        token-key: '{{.credential.access_token}}'
      name: gcp
""".format(info[2]['clusterCaCertificate'], info[1], '{0}_{1}_{2}'.format(project, zone, info[0])))

# Make a Kubernetes provider instance that uses our cluster from above.
k8s_provider = Provider('gke_k8s', kubeconfig=k8s_config)


# Finally, export the kubeconfig so that the client can easily access the cluster.
export('kubeconfig', k8s_config)


nodepool = pulumi_gcp.container.NodePool(
    'nodepool-1',
    cluster = k8s_cluster.name,
    node_config = pulumi_gcp.container.NodePoolNodeConfigArgs(
        machine_type='n1-standard-1'
    ),
    autoscaling = pulumi_gcp.container.NodePoolAutoscalingArgs(
        min_node_count = 0,
        max_node_count = 20
    )
)

#Create a canary deployment to test that this cluster works.

labels = { 'app': 'canary-{0}-{1}'.format(get_project(), get_stack()) }
canary = Deployment('canary',
    spec=DeploymentSpecArgs(
        selector=LabelSelectorArgs(match_labels=labels),
        replicas=1,
        template=PodTemplateSpecArgs(
            metadata=ObjectMetaArgs(labels=labels),
            spec=PodSpecArgs(containers=[ContainerArgs(name='nginx', image='nginx')]),
        ),
    ), __opts__=ResourceOptions(provider=k8s_provider)
)

# RBAC
#
# ClusterRole

orchestra_cluster_role = ClusterRole(
    "orchestra",
    metadata={
        "name": "orchestra-{0}-{1}-cluster-role".format(get_project(), get_stack()),
        "namespace": "default"
    },
    rules = [
        {
            "apiGroups": [""],
            "resources": ["events"],
            "verbs": ["create", "update"]
        },
        {
            "apiGroups": [""],
            "resources": ["services"],
            "verbs": ["create", "update", "get", "watch", "delete"]
        },
        {
            "apiGroups": ["extensions"],
            "resources": ["ingresses"],
            "verbs": ["create", "update", "get", "watch", "delete"]
        },
        {
            "apiGroups": ["apps"],
            "resources": ["deployments"],
            "verbs": ["create", "update", "get", "watch", "delete"]
        },
        {
            "apiGroups": [""],
            "resources": ["pods/evictions"],
            "verbs": ["create"]
        },
        {
            "apiGroups": ["rbac.authorization.k8s.io"],
            "resources": ["*"],
            "verbs": ["*"]
        }
    ],
    __opts__=ResourceOptions(provider=k8s_provider)
)

orchestra_service_account = ServiceAccount(
    "orchestra",
    metadata = {
        "name": "orchestra-service-account".format(get_project(), get_stack()),
        "namespace": "default"
    },
    __opts__=ResourceOptions(provider=k8s_provider)
)



orchestra_cluster_role_binding = ClusterRoleBinding(
    "orchestra",
    metadata={
        "name": "orchestra-{0}-{1}-cluster-role-binding".format(get_project(), get_stack()),
        "namespace": "default"
    },
    role_ref = {
        "api_group": "rbac.authorization.k8s.io",
        "kind": "ClusterRole",
        "name": "cluster-admin"
    },
    subjects = [
        {
            "kind": "ServiceAccount",
            "name": "default",
            "namespace": "default"
        },
        {
            "kind": "ServiceAccount",
            "name": "orchestra-service-account",
            "namespace": "default"
        },
        {
            "kind": "User",
            "name": "orchestra-sa@nih-strides-orchestra.iam.gserviceaccount.com"
        }
    ],
    __opts__=ResourceOptions(provider=k8s_provider)
)

# kind: ClusterRole
# apiVersion: rbac.authorization.k8s.io/v1
# metadata:
#   name: workshop-orchestra-cluster-role
#   namespace: default
# rules:
# - apiGroups: [""]
#   resources: ["events"]
#   verbs: ["create", "update"]
# - apiGroups: [""]
#   resources: ["services"]
#   verbs: ["get", "watch", "list", "create", "delete"]
# - apiGroups: ["extensions"]
#   resources: ["ingresses"]
#   verbs: ["get", "watch", "list", "create", "delete"]
# - apiGroups: ["apps"]
#   resources: ["deployments"]
#   verbs: ["get", "create", "watch", "list", "delete"]
# - apiGroups: [""]
#   resources: ["pods/eviction"]
#   verbs: ["create"]
# ---
# apiVersion: v1
# kind: ServiceAccount
# metadata:
#   name: workshop-orchestra-sa
#   namespace: default
# ---
# apiVersion: rbac.authorization.k8s.io/v1
# kind: ClusterRoleBinding
# metadata:
#   name: workshop-orchestra-cluster-role-binding
#   namespace: default
# roleRef:
#   apiGroup: rbac.authorization.k8s.io
#   kind: ClusterRole
#   name: workshop-orchestra-cluster-role
# subjects:
#   - name: workshop-orchestra-sa
#     kind: ServiceAccount
#     namespace: default


orchestra_app_name='orchestra'
orchestra_app_labels={"app": '{0}-{1}-{2}'.format(
    orchestra_app_name,
    get_project(),
    get_stack()
)}
orchestra = Deployment(
    orchestra_app_name,
    spec={
        "replicas": 2,
        "selector": {"match_labels": orchestra_app_labels},
        "template": {
            "metadata": {
                "labels": orchestra_app_labels,
                "annotations": {
                    "prometheus.io/scrape": "true",
                    "prometheus.io/path": "/metrics",
                    "prometheus.io/port": "80"
                }
            },
            "spec": {
                "containers": [
                    {
                        "name": orchestra_app_name,
                        "image": "seandavi/workshop-orchestra",
                        "resources": {
                            "requests": {
                                "memory": "1024Mi",
                                "cpu": "250m"
                            }
                        },
                        "env": [
                            {
                                "name": "API_KEY",
                                "value": "bioc2020"
                            },
                            {
                                "name": "SQLALCHEMY_URI",
                                "value": "postgresql://postgres:***REMOVED***@omicidx.cpmth1vkdqqx.us-east-1.rds.amazonaws.com/workshop_dev"
                            }
                        ]
                    }
                ]
            }
        }
    },
    __opts__=ResourceOptions(provider=k8s_provider)
)

ingress = Service(
    'ingress',
    spec=ServiceSpecArgs(
        type='LoadBalancer',
        selector=orchestra_app_labels,
        ports=[ServicePortArgs(port=80)],
    ),
    __opts__=ResourceOptions(provider=k8s_provider)
)

# Export the k8s ingress IP to access the canary deployment
export('ingress_ip', ingress.status.apply(lambda status: status.load_balancer.ingress[0].ip))
