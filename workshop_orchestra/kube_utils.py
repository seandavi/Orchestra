from kubernetes import client, config
import os
import workshop_orchestra.db as db

namespace = 'default'
if os.getenv('KUBERNETES_SERVICE_HOST'):
    config.load_incluster_config()
else:
    config.load_kube_config()

async def get_deployment(name):
    api_instance = client.AppsV1Api()
    res = api_instance.read_namespaced_deployment(name,'default')
    return res


def deployment_is_ready(name):
    api_instance = client.AppsV1Api()
    ready_replicas = api_instance.read_namespaced_deployment(name,'default').status.ready_replicas
    return ready_replicas is not None


def list_deployments():
    api_instance = client.AppsV1Api()
    return api_instance.list_namespaced_deployment(namespace, pretty=True)


def list_ingresses():
    api_instance = client.ExtensionsV1beta1Api()
    return api_instance.list_namespaced_ingress(namespace, pretty=True)


def list_services():
    api_instance = client.CoreV1Api()
    return api_instance.list_namespaced_service(namespace, pretty=True)

def delete_service(name):
    api_instance = client.CoreV1Api()
    return api_instance.delete_namespaced_service(name, namespace, pretty=True)

def delete_ingress(name):
    api_instance = client.ExtensionsV1beta1Api()
    return api_instance.delete_namespaced_ingress(name, namespace, pretty=True)

def delete_deployment(name):
    api_instance = client.AppsV1Api()
    return api_instance.delete_namespaced_deployment(name, namespace, pretty=True)

async def delete_workshop(name):
    await db.delete_instance(name)
    delete_ingress(name)
    delete_service(name)
    delete_deployment(name)

def create_ingress(api_instance, name):
    ingress = {
        "kind": "Ingress",
        "metadata": {
            "name": f"{name}",
            "labels": {
                "org": "bioc"
            },
            "annotations": {
                "kubernetes.io/ingress.class": "traefik"
            }
        },
        "spec": {
            "rules": [
                {
                    "host": f"{name}.orchestra.cancerdatasci.org",
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "backend": {
                                    "serviceName": f"{name}",
                                    "servicePort": 80
                                }
                            }
                        ]
                    }
                }
            ]
        }
    }
    try:
        api_response = api_instance.create_namespaced_ingress(namespace, ingress, pretty='true')
        print(api_response)
    except Exception as e:
        print("Exception when calling CoreV1Api->create_namespaced_endpoints: %s\n" % e)


def create_deployment(api_instance, name, container, email):
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"{name}",
            "labels": {
                "app": f"{name}",
                "org": "bioc",

            }
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": f"{name}"
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": f"{name}",
                        "base": "rstudio"
                        }
                },
                "spec": {
                    "containers": [
                        {
                            "name": f"{name}",
                            "image": container,
                            "env": [
                                {
                                    "name": "PASSWORD",
                                    "value": "welcome-to-bioc2020"
                                },
                            ],
                            "ports": [
                                {
                                    "containerPort": 8787
                                }
                            ],
                            "resources": {
                                "requests": {
                                    "memory": "1000Mi",
                                    "cpu": "100m"
                                },
                                "limits": {
                                    "memory": "10000Mi",
                                    "cpu": "1000m"
                                }
                            }
                        }
                    ]
                }
            }
        }
    }

    try:
        api_response = api_instance.create_namespaced_deployment(
            namespace, deployment, pretty='true')
        print(api_response)
    except Exception as e:
        print("Exception when calling CoreV1Api->create_namespaced_endpoints: %s\n" % e)


def create_service(api_instance, name):

    service = {
        "kind": "Service",
        "apiVersion": "v1",
        "metadata": {
            "name": f"{name}",
            "labels": {
                "org": "bioc"
            }
        },
        "spec": {
            "type": "ClusterIP",
            "selector": {
                "app": f"{name}"
            },
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 80,
                    "targetPort": 8787
                }
            ]
        }
    }

    try:
        api_response = api_instance.create_namespaced_service(namespace, service, pretty='true')
        print(api_response)
    except Exception as e:
        print("Exception when calling CoreV1Api->create_namespaced_endpoints: %s\n" % e)

def create_instance(name, container, email):
    api_instance = client.AppsV1Api()
    namespace = 'default'
    create_deployment(api_instance,name,container, email)
    api_instance = client.CoreV1Api()
    create_service(api_instance,name)
    api_instance = client.ExtensionsV1beta1Api()
    create_ingress(api_instance,name)


import click

@click.command()
@click.option('--name', prompt='Your name',
              help='The person to greet.')
@click.option('--container', prompt='Container name',
              help='The container to deploy', default='waldronlab/publicdataresources')
def main(name, container):
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    create_instance(name, container)


if __name__ == '__main__':
    main()
    
