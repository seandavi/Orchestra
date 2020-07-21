from kubernetes import client, config

namespace = 'default'

def list_deployments():
    config.load_kube_config()
    api_instance = client.AppsV1Api()
    return api_instance.list_namespaced_deployment(namespace, pretty=True)


def list_ingresses():
    config.load_kube_config()
    api_instance = client.ExtensionsV1beta1Api()
    return api_instance.list_namespaced_ingress(namespace, pretty=True)


def list_services():
    config.load_kube_config()
    api_instance = client.CoreV1Api()
    return api_instance.list_namespaced_service(namespace, pretty=True)


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
                    "host": f"{name}.bioc.cancerdatasci.org",
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


def create_deployment(api_instance, name, container):
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": f"{name}",
            "labels": {
                "app": f"{name}",
                "org": "bioc"
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
                        "app": f"{name}"
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
                                    "memory": "5000Mi",
                                    "cpu": "500m"
                                },
                                "limits": {
                                    "memory": "5000Mi",
                                    "cpu": "1800m"
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

def create_instance(name, container):
    config.load_kube_config()
    api_instance = client.AppsV1Api()
    namespace = 'default'
    create_deployment(api_instance,name,container)
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
    
