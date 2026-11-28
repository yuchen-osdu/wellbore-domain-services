<!--- Deploy -->

# CORE Wellbore service

## Introduction

This chart deploys wellbore service on a [Kubernetes](https://kubernetes.io) cluster using [Helm](https://helm.sh) package manager.

## Prerequisites

|The code was tested on **Kubernetes cluster** (v1.23.12) with **Istio** (1.15)
> It is possible to use other versions, but it hasn't been tested

### Operation system

The code works in Debian-based Linux (Debian 10 and Ubuntu 20.04) and Windows WSL 2. Also, it works but is not guaranteed in Google Cloud Shell. All other operating systems, including macOS, are not verified and supported.

### Packages

Packages are only needed for installation from a local computer.

- **HELM** (version: v3.7.1 or higher) [helm](https://helm.sh/docs/intro/install/)
- **Kubectl** (version: v1.23.12 or higher) [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl)

## Installation

You need to set variables in **values.yaml** file using any code editor. Some of the values are prefilled, but you need to specify some values as well. You can find more information about them below.

### Global variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
|**global.domain** | your domain, ex `example.com`. Not used by this chart, but may be used in different deployment setups. Use `global.hostname` for the route host | string | - | no |
|**global.hostname** | host the `HTTPRoute` attaches to when `httpRoute.hostnames` is empty, ex `osdu.example.com` | string | `""` | only if `httpRoute.enabled` is true and `httpRoute.hostnames` is empty |
|**global.limitsEnabled** | whether CPU and memory limits are enabled | boolean | true | yes |

### Configmap variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
|**data.WDMSWorkerHost** | wellbore-worker URL | string | `http://wellbore-worker` | yes |

### Deployment variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
|**data.requestsCpu** | amount of requested CPU | string | `130m` | yes |
|**data.requestsMemory** | amount of requested memory| string | `750Mi` | yes |
|**data.limitsCpu** | CPU limit | string | `1` | only if `global.limitsEnabled` is true |
|**data.limitsMemory** | memory limit | string | `3G` | only if `global.limitsEnabled` is true |
|**data.serviceAccountName** | name of your service account | string | `wellbore` | yes |
|**data.imagePullPolicy** | when to pull image | string | `IfNotPresent` | yes |
|**data.image** | service image | string | - | yes |

### Configuration variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
|**conf.appName** | Service name | string | `wellbore` | yes |
|**conf.configmap** | configmap to be used | string | `wellbore-config` | yes |
|**conf.keycloakSecretName** | Keycloak secret name | string | `wellbore-keycloak-secret` | yes |
|**conf.s3SecretName** | secret for S3/SeaweedFS storage(prefixed with `global.dataPartitionId`) | string | `wellbore-seaweedfs-secret` | yes |
|**conf.replicas** | Number of pods for service | integer | 2 | yes |

### ISTIO variables

| Name | Description | Type | Default |Required |
|------|-------------|------|---------|---------|
|**istio.proxyCPU** | CPU request for Envoy sidecars | string | 10m | yes |
|**istio.proxyCPULimit** | CPU limit for Envoy sidecars | string | 500m | yes |
|**istio.proxyMemory** | memory request for Envoy sidecars | string | 100Mi | yes |
|**istio.proxyMemoryLimit** | memory limit for Envoy sidecars | string | 512Mi | yes |

### Routing (HTTPRoute)

The chart owns the routing for the service. It renders a Gateway API `HTTPRoute`, disabled by default. The chart no longer ships an Istio `VirtualService`.

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
|**httpRoute.enabled** | render the `HTTPRoute` | boolean | `false` | yes |
|**httpRoute.name** | route name. When empty the name is `<release>-route`, which differs from any route of the same name defined outside this chart | string | `""` | no |
|**httpRoute.parentRefs** | gateways the route attaches to | list | `cimpl-gateway` in `istio-system` | yes |
|**httpRoute.hostnames** | hosts the route serves. When empty, `global.hostname` is used | list | `[]` | one of `httpRoute.hostnames` or `global.hostname` |
|**httpRoute.routes** | one rule per entry, see below | list | `/api/os-wellbore-ddms/` | yes |

The render fails when `httpRoute.enabled` is true and both `httpRoute.hostnames` and `global.hostname` are empty, so the route is never exposed on all hosts.

Each entry of `httpRoute.routes` accepts:

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
|**path** | path to match | string | - | yes |
|**pathType** | match type, `PathPrefix` or `Exact` | string | `PathPrefix` | no |
|**serviceName** | backend Service name | string | `conf.appName` | no |
|**port** | backend Service port | integer | `80` | no |
|**filters** | Gateway API filters, for example `URLRewrite` | list | - | no |

Example, a route with a rewrite and another port:

```yaml
httpRoute:
  enabled: true
  hostnames:
    - osdu.example.com
  routes:
    - path: /api/os-wellbore-ddms/
    - path: /other/
      port: 9002
      filters:
        - type: URLRewrite
          urlRewrite:
            path:
              type: ReplacePrefixMatch
              replacePrefixMatch: /
```

## Install the Helm chart

Run this command from within this directory:

```console
helm install wellbore-deploy .
```

To expose the service through the Gateway API:

```console
helm install wellbore-deploy . --set httpRoute.enabled=true --set global.hostname=osdu.example.com
```

To check the rendered route without installing:

```console
helm template wellbore-deploy . --set httpRoute.enabled=true --set global.hostname=osdu.example.com -s templates/httproute.yaml
```

## Uninstall the Helm chart

To uninstall the helm deployment:

```console
helm uninstall wellbore-deploy
```

> Do not forget to delete all k8s secrets and PVCs accociated with the Service.

[Move-to-Top](#deploy-helm-chart)
