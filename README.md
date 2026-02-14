# Production-Grade Kubernetes Cluster on AWS

A self-managed Kubernetes cluster built with kubeadm on AWS EC2, enhanced from a basic working setup to production-grade standards with GitOps, CI/CD, RBAC, autoscaling, and comprehensive monitoring.

## Architecture

```
                            Internet
                               |
                          [ AWS ALB ]
                               |
                    ┌──────────┴─────────────┐
                    |      VPC (Private)     |
                    |                        |
                    |      Control Plane     |
                    |       (kubeadm)        |
                    |                        |
                    |  Worker 1    Worker 2  |
                    |   ┌─────┐    ┌─────┐   |
                    |   │Pods │    │Pods │   |
                    |   └─────┘    └─────┘   |
                    └────────────────────────┘
```

**Traffic flow:** Internet → ALB:80 → NodePort:30080 → Frontend Pod:5000 → API Pod:5000 → Redis Pod:6379

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
| GitOps           | ArgoCD (app-of-apps pattern)                                         |
| CI/CD            | GitHub Actions (build, scan, push, deploy)                           |
| Monitoring       | Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics |
| Security         | Network Policies, RBAC, Sealed Secrets, Trivy image scanning         |
| Autoscaling      | HPA with metrics-server                                              |

## Project Structure

```
├── .github/workflows/
│   └── build.yaml              # CI/CD pipeline
├── infrastructure/             # terraform
│   ├── main.tf
│   ├── vpc.tf
│   ├── instances.tf
│   ├── security-groups.tf
│   ├── alb.tf
│   ├── iam.tf
│   ├── s3.tf
│   ├── variables.tf
│   └── outputs.tf
├── ansible/                    # cluster provisioning
│   ├── site.yaml
│   ├── ansible.cfg
│   ├── inventory.aws_ec2.yaml
│   ├── group_vars/all/
│   └── roles/
│       ├── common/             # OS config, containerd, kubeadm
│       ├── control_plane/      # cluster init, Canal CNI
│       ├── worker/             # node join
│       ├── apps/               # prerequisites (metrics-server, sealed-secrets, PV dirs)
│       └── argocd/             # ArgoCD install + bootstrap
├── kubernetes/
│   ├── argocd/
│   │   ├── bootstrap.yaml      # app-of-apps entry point
│   │   └── applications/       # ArgoCD Application definitions
│   ├── namespaces/             # production, staging, monitoring
│   ├── production/             # app deployments, services, configmaps, secrets, HPAs
│   ├── monitoring/             # Prometheus, Grafana, Alertmanager stack
│   ├── network-policies/       # pod-to-pod traffic rules
│   └── storage/                # EBS StorageClass, PVCs
└──application/
    ├── api/                    # Flask API + Dockerfile
    └── frontend/               # Flask frontend + Dockerfile
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

Wait 2 minutes for SSM agent registration:

```bash
aws ssm describe-instance-information --region us-east-1 \
  --query 'InstanceInformationList[*].[InstanceId,PingStatus]' --output table
```

### Provision Cluster

```bash
cd ansible
ansible-playbook site.yaml
```

This installs kubeadm, initializes the control plane, joins workers, installs Canal CNI, metrics-server, Sealed Secrets controller, ArgoCD, and bootstraps all applications via GitOps.

### Create Secrets

After the playbook completes, SSM into the control plane and create the application secrets:

```bash
aws ssm start-session --target <control-plane-id> --region us-east-1

kubectl create secret generic app-secret \
  --namespace=production \
  --from-literal=REDIS_PASSWORD='your-password'

kubectl create secret generic grafana-secret \
  --namespace=monitoring \
  --from-literal=admin-password='your-password'

kubectl create secret generic alertmanager-config \
  --namespace=monitoring \
  --from-literal=alertmanager.yml='<alertmanager config with webhook URL>'
```

### Verify

```bash
kubectl get pods -A
kubectl get applications -n argocd
```

### Access

| Service      | URL                     |
|--------------|-------------------------|
| Application  | `http://<ALB-DNS>`      |
| Grafana      | `http://<ALB-DNS>:3000` |
| Prometheus   | `http://<ALB-DNS>:9090` |
| Alertmanager | `http://<ALB-DNS>:9093` |
| ArgoCD       | `http://<ALB-DNS>:8080` |

Get the ALB DNS: `terraform output alb_dns_name`

### Tear Down

```bash
cd infrastructure
terraform destroy
```

## CI/CD Pipeline

The GitHub Actions pipeline triggers on pushes to `application/` on the `main` branch.

**Stages:** Detect changes → Build Docker image → Scan with Trivy → Push to Docker Hub → Update Kubernetes manifest → ArgoCD deploys automatically

The pipeline never touches the cluster directly. It pushes a manifest change to Git, and ArgoCD handles deployment. This means CI/CD credentials never include cluster access.

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

All Applications use auto-sync with self-heal and pruning enabled. Changes pushed to Git are automatically applied. Manual cluster changes are reverted.

## Monitoring

**Configured alerts:**
- NodeDown (critical)
- HighMemoryUsage > 80% (warning)
- HighCPUUsage > 80% (warning)
- PodCrashLooping (warning)
- PodNotReady (warning)

Alerts route to Slack via Alertmanager.

## Security

- **Network Policies:** Pod-to-pod traffic restricted by Canal (Calico policy enforcement)
- **RBAC:** Dedicated ServiceAccounts per application component (some with default no permissions because there was no need for it)
- **Secrets:** Sealed Secrets controller installed for GitOps-compatible secret management
- **Image scanning:** Trivy scans every image build for CRITICAL vulnerabilities before push
- **No SSH:** All node access via AWS SSM Session Manager
- **Private subnets:** All nodes in private subnets, internet access via NAT Gateway

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