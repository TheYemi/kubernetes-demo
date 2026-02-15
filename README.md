# Production-Grade Kubernetes Cluster on AWS

A self-managed Kubernetes cluster built with kubeadm on AWS EC2, enhanced from a basic working setup to production-grade standards with GitOps, CI/CD, RBAC, autoscaling, and comprehensive monitoring.

## Architecture

```
                                Internet
                                    |
                               [ AWS ALB ]
                                    |
                         ALB:80 → NodePort:30080
                                    |
                    ┌───────────────┴───────────────┐
                    |        VPC (Private)          |
                    |                               |
                    |    NGINX Ingress Controller   |
                    |       ┌─────────────┐         |
                    |       │ Path-based  │         |
                    |       │  routing    │         |
                    |       └──────┬──────┘         |
                    |              |                |
                    |   /            → Frontend     |
                    |   /grafana     → Grafana      |
                    |   /prometheus  → Prometheus   |
                    | /alertmanager  → Alertmanager |
                    |   /argocd      → ArgoCD       |
                    |                               |
                    |      Control Plane            |
                    |       (kubeadm)               |
                    |                               |
                    |    Worker 1    Worker 2       |
                    |     ┌─────┐    ┌─────┐        |
                    |     │Pods │    │Pods │        |
                    |     └─────┘    └─────┘        |
                    └───────────────────────────────┘
```

**Traffic flow:** Internet → ALB:80 → NodePort:30080 → NGINX Ingress → Path-based routing to ClusterIP services

**Application:**

```
Frontend (Flask) → API (Flask) → Redis (Persistent)
```

Network Policies enforce strict communication: Frontend can only reach API, API can only reach Redis, Redis only accepts connections from API.

## Tech Stack

| Layer            | Tools                                                                |
|------------------|----------------------------------------------------------------------| 
| Infrastructure   | Terraform (VPC, EC2, ALB, NAT Gateway, S3)                           |
| Provisioning     | Ansible via SSM (no SSH keys)                                        |
| Orchestration    | kubeadm, Canal CNI (Flannel + Calico)                                |
| Ingress          | NGINX Ingress Controller (path-based routing)                        |
| GitOps           | ArgoCD (app-of-apps pattern)                                         |
| CI/CD            | GitHub Actions (build, scan, push, deploy)                           |
| Monitoring       | Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics |
| Storage          | AWS EBS CSI Driver, gp3 StorageClass                                 |
| Security         | Network Policies, RBAC, Sealed Secrets, Trivy image scanning         |
| Autoscaling      | HPA with metrics-server                                              |

## Project Structure

```
├── .github/workflows/
│   └── build.yaml                    # CI/CD pipeline
├── infrastructure/                   # Terraform
│   ├── main.tf                       # Provider config
│   ├── vpc.tf                        # VPC, subnets, NAT Gateway
│   ├── instances.tf                  # EC2 instances (control plane + 2 workers)
│   ├── security-groups.tf            # Node SG + ALB-to-Ingress rule
│   ├── alb.tf                        # ALB, single target group (port 30080)
│   ├── iam.tf                        # SSM, S3, EBS CSI IAM policies
│   ├── s3.tf                         # S3 bucket for Ansible SSM connection
│   ├── variables.tf
│   └── outputs.tf
├── ansible/                          # Cluster provisioning
│   ├── site.yaml                     # Main playbook
│   ├── ansible.cfg
│   ├── inventory.aws_ec2.yaml        # Dynamic EC2 inventory
│   ├── group_vars/all/
│   └── roles/
│       ├── common/                   # OS config, containerd, kubeadm
│       ├── control_plane/            # Cluster init, Canal CNI
│       ├── worker/                   # Node join
│       ├── apps/                     # metrics-server, Sealed Secrets, EBS CSI, NGINX Ingress
│       └── argocd/                   # ArgoCD install + bootstrap
├── kubernetes/
│   ├── argocd/
│   │   ├── bootstrap.yaml            # App-of-apps entry point
│   │   ├── argocd-deployer-rbac.yaml # ArgoCD RBAC
│   │   └── applications/             # ArgoCD Application definitions
│   │       ├── namespace.yaml
│   │       ├── storage.yaml
│   │       ├── production.yaml
│   │       ├── monitoring.yaml
│   │       ├── network-policies.yaml
│   │       └── ingress.yaml
│   ├── namespaces/                   # production, staging, monitoring
│   ├── production/                   # App deployments, services, HPAs, sealed secrets
│   ├── monitoring/                   # Prometheus, Grafana, Alertmanager stack
│   ├── network-policies/             # Pod-to-pod traffic rules
│   ├── ingress/                      # NGINX Ingress routing rules
│   ├── storage/                      # EBS StorageClass, PVCs
│   └── secrets/                      # Secret example templates (.example files)
└── application/
    ├── api/                          # Flask API + Dockerfile
    └── frontend/                     # Flask frontend + Dockerfile
```

## Deployment

### Prerequisites

- AWS account with credentials configured
- Terraform installed
- Ansible installed with `amazon.aws` collection
- SSM Session Manager plugin installed
- Docker Hub account (for CI/CD image pushes)

### Deploy Infrastructure

```bash
cd infrastructure
terraform init
terraform apply
```

Wait for SSM agent registration:

```bash
aws ssm describe-instance-information --region us-east-1 \
  --query 'InstanceInformationList[*].[InstanceId,PingStatus]' --output table
```

### Provision Cluster

```bash
cd ansible
ansible-playbook site.yaml
```

This installs kubeadm, initializes the control plane, joins workers, and installs Canal CNI, metrics-server, Sealed Secrets controller, EBS CSI driver, NGINX Ingress controller, ArgoCD, and bootstraps all applications via GitOps.

### Seal and Deploy Secrets
After the cluster is provisioned, pods will be in `CreateContainerConfigError` because secrets don't exist yet. The Sealed Secrets controller generates a unique key pair per cluster, so secrets must be sealed with the current cluster's certificate.

1. Fetch the cluster's public certificate from the control plane:

```bash
aws ssm start-session --target <control-plane-id> --region us-east-1


kubectl get secret -n kube-system \
  -l sealedsecrets.bitnami.com/sealed-secrets-key \
  -o jsonpath='{.items[0].data.tls\.crt}' | base64 -d > pub-cert.pem
```
2. Copy `pub-cert.pem` to your local machine and create temporary plaintext secret files using the templates in `kubernetes/secrets/`:

```bash
# Create plaintext secrets from the example templates (never commit these)
kubeseal --cert pub-cert.pem --format yaml < /tmp/app-secret.yaml > kubernetes/production/app-sealed-secret.yaml
kubeseal --cert pub-cert.pem --format yaml < /tmp/grafana-secret.yaml > kubernetes/monitoring/grafana-sealed-secret.yaml
kubeseal --cert pub-cert.pem --format yaml < /tmp/alertmanager-secret.yaml > kubernetes/monitoring/alertmanager-sealed-secret.yaml
```
3. Push the sealed secrets to Git. ArgoCD syncs them, the controller decrypts, and pods start.
4. Delete the plaintext files and `pub-cert.pem`.

### Verify

```bash
kubectl get pods -A
kubectl get applications -n argocd
```

### Access
All services are accessible through a single ALB endpoint via path-based routing:

| Service      | URL                             |
|--------------|---------------------------------|
| Application  | `http://<ALB-DNS>`              |
| Grafana      | `http://<ALB-DNS>/grafana`      |
| Prometheus   | `http://<ALB-DNS>/prometheus`   |
| Alertmanager | `http://<ALB-DNS>/alertmanager` |
| ArgoCD       | `http://<ALB-DNS>/argocd`       |

Get the ALB DNS: `terraform -chdir=infrastructure output alb_dns_name`

### Tear Down
```bash
cd infrastructure
terraform destroy
```

## Ingress
An NGINX Ingress controller handles all external routing through a single NodePort (30080). The ALB forwards all traffic to this one port, and NGINX routes requests to the correct ClusterIP service based on the URL path.
This replaces the previous setup where each service needed its own NodePort, ALB target group, and listener. Adding a new service now only requires an Ingress YAML manifest, no Terraform changes needed.
Services that run under a subpath are configured to be aware of their prefix: Grafana uses GF_SERVER_SERVE_FROM_SUB_PATH, Prometheus and Alertmanager use --web.external-url, and ArgoCD uses NGINX rewrite rules to strip the /argocd prefix.

## CI/CD Pipeline
The GitHub Actions pipeline triggers on pushes to `application/` on the `main` branch.

**Stages:** Detect changes → Build Docker image → Scan with Trivy → Push to Docker Hub → Update Kubernetes manifest → ArgoCD deploys automatically

The pipeline uses dorny/paths-filter to detect whether the API, frontend, or both changed, and only builds what's necessary. It never touches the cluster directly, it updates the image tag in the deployment manifest and pushes to Git. ArgoCD picks up the change and deploys.

**Required GitHub Secrets:**
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## GitOps with ArgoCD
ArgoCD uses the app-of-apps pattern. A single bootstrap Application watches `kubernetes/argocd/applications/`, which contains Application definitions for each component:

- `namespaces` — cluster namespace definitions
- `storage` — StorageClass, PVs, PVCs
- `production` — application deployments, services, configs, HPAs
- `monitoring` — Prometheus, Grafana, Alertmanager stack
- `network-policies` — pod-to-pod traffic rules
- `ingress` — NGINX Ingress routing rules

All Applications use auto-sync with self-heal and pruning enabled. Changes pushed to Git are automatically applied. Manual cluster changes are reverted.

## Monitoring
Stack: Prometheus scrapes metrics, Alertmanager handles alert routing to Slack, Grafana provides dashboards, node-exporter exposes host metrics, kube-state-metrics exposes Kubernetes object metrics.

**Configured alerts:**
- NodeDown (critical)
- HighMemoryUsage > 80% (warning)
- HighCPUUsage > 80% (warning)
- PodCrashLooping (warning)
- PodNotReady (warning)

Alerts route to Slack via Alertmanager.

Note: Prometheus is configured to only scrape worker node-exporters, excluding the control plane via relabel config.

## Security
- **Network Policies:** Pod-to-pod traffic restricted by Canal (Calico policy enforcement)
- **RBAC:** Dedicated ServiceAccounts per application component (some with default no permissions because there was no need for it)
- **Sealed Secrets:** Secrets are encrypted with the cluster's public certificate and stored in Git. Only the controller's private key can decrypt them. Example templates in kubernetes/secrets/.
- **Image scanning:** Trivy scans every image build for CRITICAL vulnerabilities before push. Builds fail if vulnerabilities are found.
- **No SSH:** All node access via AWS SSM Session Manager
- **Private subnets:** All nodes in private subnets, internet access via NAT Gateway
- **Non-root containers:** Application Dockerfiles create and run as a dedicated `appuser`.

## Storage
Persistent storage uses the AWS EBS CSI driver with a gp3 StorageClass. Volumes are encrypted and support expansion. `WaitForFirstConsumer` binding ensures volumes are created in the same AZ as the pod.

### Persistent volumes:
Redis (2Gi) — append-only data persistence
Grafana (2Gi) — dashboard and data source storage

## Autoscaling
HPA configured for frontend and API deployments:
- Target CPU utilization: 70%
- Min replicas: 2
- Max replicas: 6

Metrics-server installed with `--kubelet-insecure-tls` for self-managed cluster compatibility.

## Cost

Running costs approximately $0.17/hour:
- 3x c7i-flex.large instances
- NAT Gateway
- ALB

NAT Gateway and ALB charge even when instances are stopped. Use `terraform destroy` when not in use.