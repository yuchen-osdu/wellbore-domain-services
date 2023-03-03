# Helm Chart

## Introduction
The following document outlines how to deploy and update the service application onto an existing Kubernetes deployment using the [Helm](https://helm.sh) package manager.

## Prerequisites
The below software must be installed before continuing:
* [AWS CLI ^2.7.0](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
* [kubectl 1.21-1.22](https://kubernetes.io/docs/tasks/tools/)
* [Helm ^3.7.1](https://helm.sh/docs/intro/install/)
* [Helm S3 Plugin ^0.12.0](https://github.com/hypnoglow/helm-s3)

Additionally, an OSDU on AWS environment must be deployed.

## Installation/Updating
To install or update the service application by executing the following command in the CHART folder:

```bash
helm upgrade [RELEASE_NAME] . -i -n [NAMESPACE]
```

To observe the Kubernetes resources before deploying them using the command:
```bash
helm upgrade [RELEASE_NAME] . -i -n [NAMESPACE] --dry-run --debug
```

To observe the history of the current release, use the following command:
```bash
helm history [RELEASE_NAME] -n [NAMESPACE]
```

To revert to a previous release, use the following command:
```bash
helm rollback [RELEASE] [REVISION] -n [NAMESPACE]
```

### Customizing the Deployment
It is possible to modify the default values specified in the **values.yaml** file using the --set option. The below parameters can be modified by advanced users to customize the deployment configuration:

| Name | Example Value | Description | Type | Required |
| ---  | ------------- | ----------- | ---- | -------- |
| `global.accountID` | `000123456789` | The AWS account ID. | int | yes |
| `global.region` | `us-east-1` | The AWS region containing the OSDU deployment. | str | yes |
| `global.resourcePrefix` | `osdu` | The resource prefix of the OSDU deployment. | str | yes |
| `global.allowOrigins` | `{http://localhost,https://www.osdu.aws}` | A list of domains that are permitted by CORS policy. An empty list permits all origins. | array[str] | no |
| `podAnnotations` | `podAnnotations.version=v1.0.0` | Additional annotations on the service pod | dict | no |
| `imagePullPolicy` | `IfNotPresent` | The service image pull policy | str | no |
| `replicaCount` | `1` | The number of pod replicas to be deployed | int | no |
| `autoscaling.minReplicas` | `1` | Minimum number of pod replicas | int | no |
| `autoscaling.maxReplicas` | `100` | Maximum number of pod replicas | int | no |
| `autoscaling.targetCPUUtilizationPercentage` | `80` | CPU utilization target | int | no |

## Uninstalling the Chart
To uninstall the helm release:

```bash
helm uninstall [RELEASE] -n [NAMESPACE] --keep-history
```