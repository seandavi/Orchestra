from kubernetes import client, config
import os
import string
import random
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

def hash_key(key: str, k: int=8) -> str:
    """Generate a random string

    Parameters:

    k: int length of resulting string
    """
    if(k>32):
        k=32
    return hashlib.sha1(key).hexdigest()[:k]

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

def delete_virtual_service(name):
    api_instance = client.CustomObjectsApi()
    return api_instance.delete_namespaced_custom_object(
        group='networking.istio.io',
        version='v1alpha3',
        name=name, namespace=namespace,
        plural='virtualservices')

async def delete_workshop(name):
    #await db.delete_instance(name)
    # delete_ingress(name)
    delete_virtual_service(name)
    delete_service(name)
    delete_deployment(name)

def create_virtual_service(api_instance, name):
    crd_body = {
        "apiVersion": "networking.istio.io/v1alpha3",
        "kind": "VirtualService",
        "metadata": {
            "name": f"{name}",
            "labels": {
                "org": "bioc"
            },
        },
        "spec": {
            "hosts": [
                f"{name}.orchestra.cancerdatasci.org"
            ],
            "gateways": [
                "orchestra-gateway"
            ],


            "http": [{
                "route": [{
                    "destination": {
                        "host": name
                    }
                }]
            }]
        }
    }
    def get_custom_object_details(crd_body):
        group = crd_body["apiVersion"].split("/")[0]
        version = crd_body["apiVersion"].split("/")[1]
        plural = crd_body["kind"].lower() + "s"
        name = crd_body["metadata"]["name"]

        return group, version, plural, name
    try:
        group, version, plural, name = get_custom_object_details(crd_body)
        api_response = api_instance.create_namespaced_custom_object(
            group=group,
            version=version,
            plural=plural,
            namespace=namespace,
            body=crd_body,
            pretty='true')
        print(api_response)
    except Exception as e:
        print("Exception when calling CoreV1Api->create_namespaced_endpoints: %s\n" % e)
        print(group, version, plural, name)


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


def create_deployment(api_instance, name, container, email, memory='1000M', cpu='100m', port=8787):
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
                                    "value": "rstudio"
                                },
                            ],
                            "ports": [
                                {
                                    "containerPort": port
                                }
                            ],
                            "resources": {
                                "requests": {
                                    "memory": memory,
                                    "cpu": cpu
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


def create_service(api_instance, name, port=8787):

    service = {
        "kind": "Service",
        "apiVersion": "v1",
        "metadata": {
            "name": f"{name}",
            ""
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
                    "targetPort": port
                }
            ]
        }
    }

    try:
        api_response = api_instance.create_namespaced_service(namespace, service, pretty='true')
        print(api_response)
    except Exception as e:
        print("Exception when calling CoreV1Api->create_namespaced_endpoints: %s\n" % e)

async def create_instance(workshop_id, email, name=None):
    workshop = await db.get_workshops(id=workshop_id)
    name = "abc123"
    container = workshop.get('container')
    api_instance = client.AppsV1Api()
    namespace = 'default'
    create_deployment(api_instance,name,container, email)
    api_instance = client.CoreV1Api()
    create_service(api_instance,name)
    # lines below are for traefik
    # Not needed since switching to istio
    # api_instance = client.ExtensionsV1beta1Api()
    # create_ingress(api_instance,name)
    api_instance = client.CustomObjectsApi()
    create_virtual_service(api_instance,name)
    return {'url': 'http://abc123.orchestra.cancerdatasci.org', 'name': name}

import click

@click.group()
def cli():
    pass

@cli.command()
@click.option('--name', prompt='Name of the instance',
              help='The name of the instance')
@click.option('--email', '-e', prompt='email')
@click.option('--workshop_id','-i', prompt='Workshop ID',
              help='The container to deploy', default=10)
def create_workshop(name, workshop_id, email):
    import asyncio
    # Configs can be set in Configuration class directly or using helper
    # utility. If no argument provided, the config will be loaded from
    # default location.
    res = asyncio.run(create_instance(name, workshop_id, email))
    return res

@cli.command()
@click.option('--name', prompt='Name of the instance',
              help='The name of the instance')
def delete(name):
    import asyncio
    res = asyncio.run(delete_workshop(name))
    return res


if __name__ == '__main__':
    cli()
