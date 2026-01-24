# Self-Managed Kubernetes Cluster on AWS

A production-style Kubernetes cluster built from scratch using kubeadm on AWS EC2, with full automation, monitoring, and network security.

## What This Project Demonstrates

- **Infrastructure as Code** — Terraform for AWS resources
- **Configuration Management** — Ansible for cluster provisioning via SSM
- **Container Orchestration** — Self-managed Kubernetes with kubeadm
- **Networking** — Canal CNI (Flannel + Calico) with Network Policies
- **Observability** — Prometheus, Alertmanager, Grafana
- **Persistent Storage** — PersistentVolumes for stateful workloads

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                            AWS                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     VPC (10.0.0.0/16)                     │  │
│  │                                                           │  │
│  │   ┌─────────────┐              ┌─────────────────────┐    │  │
│  │   │   Public    │              │   Private Subnet    │    │  │
│  │   │   Subnet    │              │                     │    │  │
│  │   │             │              │  ┌───────────────┐  │    │  │
│  │   │  ┌─────┐    │              │  │ Control Plane │  │    │  │
│  │   │  │ ALB │    │              │  │   (kubeadm)   │  │    │  │
│  │   │  └──┬──┘    │              │  └───────────────┘  │    │  │
│  │   │     │       │              │                     │    │  │
│  │   │  ┌──┴──┐    │              │  ┌─────┐  ┌─────┐   │    │  │
│  │   │  │ NAT │    │              │  │ W1  │  │ W2  │   │    │  │
│  │   │  └─────┘    │              │  └─────┘  └─────┘   │    │  │
│  │   └─────────────┘              └─────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Application Stack

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Frontend   │ ───► │     API      │ ───► │    Redis     │
│  (Flask)     │      │   (Flask)    │      │  (Persistent)│
└──────────────┘      └──────────────┘      └──────────────┘
      ▲                                            
      │                                            
   External                                        
   Traffic                                         
   (via ALB)                                       
```

**Network Policies enforce:**
- Frontend can only reach API
- API can only reach Redis
- Redis only accepts connections from API

## Tech Stack

| Layer | Tools |
|-------|-------|
| Infrastructure | Terraform, AWS (VPC, EC2, ALB, S3) |
| Provisioning | Ansible (via SSM, no SSH required) |
| Kubernetes | kubeadm, Canal CNI (Flannel + Calico) |
| Application | Python Flask, Redis |
| Monitoring | Prometheus, Alertmanager, Grafana |
| Security | Network Policies, IAM roles, Security Groups |

## Project Structure

```
k8s-project/
├── infrastructure/          # Terraform
│   ├── main.tf
│   ├── variables.tf
│   ├── vpc.tf
│   ├── security-groups.tf
│   ├── iam.tf
│   ├── instances.tf
│   ├── alb.tf
│   ├── s3.tf
│   └── outputs.tf
├── ansible/                 # Cluster provisioning
│   ├── ansible.cfg
│   ├── inventory.aws_ec2.yaml
│   ├── site.yaml
│   ├── group_vars/
│   │   └── all/
│   │       └── all.yaml
│   └── roles/
│       ├── common/
│       ├── control_plane/
│       ├── worker/
│       └── apps/
├── kubernetes/              # K8s manifests
│   ├── app/
│   ├── storage/
│   ├── monitoring/
│   └── network-policies/
└── docs/
    └── k8s-setup.md
```

## Quick Start

### Prerequisites

- AWS account with credentials configured
- Terraform installed
- Ansible installed (use WSL on Windows)
- SSM Session Manager plugin installed

### Deploy

```bash
# 1. Infrastructure
cd infrastructure
terraform init
terraform apply

# 2. Wait for SSM registration (2 minutes)
aws ssm describe-instance-information --region us-east-1

# 3. Provision cluster
cd ../ansible
ansible-playbook site.yaml

# 4. Access cluster
aws ssm start-session --target <control-plane-id> --region us-east-1
kubectl get nodes
```

### Tear Down

```bash
cd infrastructure
terraform destroy
```

## Features

### Monitoring Stack

- **Prometheus** — Metrics collection with service discovery
- **Alertmanager** — Alert routing to Slack
- **Grafana** — Dashboards with persistent storage
- **Node Exporter** — Host metrics
- **kube-state-metrics** — Kubernetes object metrics

**Configured Alerts:**
- NodeDown (critical)
- HighMemoryUsage (warning)
- HighCPUUsage (warning)
- PodCrashLooping (warning)
- PodNotReady (warning)

### Network Policies

Pod-to-pod traffic is restricted:

| Source | Destination | Allowed |
|--------|-------------|---------|
| Frontend | API | ✅ |
| Frontend | Redis | ❌ |
| API | Redis | ✅ |
| API | Frontend | ❌ |
| Any | Redis | ❌ |

### Ansible Automation

- **SSM-based** — No SSH keys required
- **Dynamic inventory** — Auto-discovers EC2 instances by tags
- **Idempotent** — Safe to run multiple times
- **Terraform integration** — Variables passed automatically

## Key Learnings

### Networking
- Canal CNI = Flannel (networking) + Calico (policy enforcement)
- Network Policies require a CNI that supports them
- DNS egress must be allowed for service name resolution

### Ansible + AWS
- SSM connection requires S3 bucket for file transfers
- `group_vars/all/` directory for global variables
- ACL package required for `become_user` functionality

### Kubernetes
- Prometheus relabel configs: missing `regex` defaults to `.*`
- Labels with empty values need `labelpresent` not `label`
- initContainers for volume permission setup

## Cost

Running costs approximately $0.17/hour:
- 3x c7i-flex.large instances
- NAT Gateway (~$0.045/hr)
- ALB (~$0.02/hr)

**Important:** NAT Gateway and ALB charge even when instances are stopped. Use `terraform destroy` when not in use.

## Future Enhancements

- [ ] Centralized logging (Fluent Bit + OpenSearch)
- [ ] Multi-AZ deployment
- [ ] Horizontal Pod Autoscaler

## Documentation

- [Kubernetes Setup Guide](docs/k8s-setup.md) — Manual and automated installation steps