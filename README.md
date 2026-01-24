# Self-Managed Kubernetes Cluster on AWS: From Infrastructure to Observability

A hands-on project building a production-style Kubernetes cluster from scratch using kubeadm on AWS EC2, deploying a three-tier microservices application with full monitoring stack.

## Why This Project?

To understand Kubernetes internals; how clusters form, how pods communicate, how networking actually works, and how to debug when things break. Theory only goes so far. This project is hands-on proof of that understanding.

## Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                            AWS                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     VPC (10.0.0.0/16)                     │  │
│  │                                                           │  │
│  │   ┌─────────────┐              ┌─────────────────────┐   │  │
│  │   │   Public    │              │   Private Subnet    │   │  │
│  │   │   Subnet    │              │                     │   │  │
│  │   │             │              │  ┌───────────────┐  │   │  │
│  │   │  ┌─────┐    │              │  │ Control Plane │  │   │  │
│  │   │  │ ALB │    │              │  │   (kubeadm)   │  │   │  │
│  │   │  └──┬──┘    │              │  └───────────────┘  │   │  │
│  │   │     │       │              │                     │   │  │
│  │   │  ┌──┴──┐    │              │  ┌─────┐  ┌─────┐  │   │  │
│  │   │  │ NAT │    │              │  │ W1  │  │ W2  │  │   │  │
│  │   │  └─────┘    │              │  └─────┘  └─────┘  │   │  │
│  │   └─────────────┘              └─────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## What's Running

**Application Stack:**
- Frontend — Flask web UI
- API — Flask REST backend
- Redis — Data store with persistent storage

**Kubernetes Components:**
- 1 Control plane node (kubeadm)
- 2 Worker nodes
- Flannel CNI for pod networking
- CoreDNS for service discovery

**Monitoring Stack:**
- Prometheus — Metrics collection
- Grafana — Dashboards
- Node-exporter — Host metrics

## Tech Stack

| Layer | Tools |
|-------|-------|
| Infrastructure | Terraform, AWS (VPC, EC2, ALB) |
| Kubernetes | kubeadm, containerd, Flannel |
| Application | Python Flask, Redis |
| Monitoring | Prometheus, Grafana |
| Configuration | ConfigMaps, Secrets, RBAC |
| Storage | PersistentVolumes (hostPath) |

## Project Structure
```
k8s-project/
├── infrastructure/          # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── vpc.tf
│   ├── security-groups.tf
│   ├── iam.tf
│   ├── instances.tf
│   ├── alb.tf
│   └── outputs.tf
├── kubernetes/              # K8s manifests
│   ├── app/
│   │   ├── frontend-deployment.yaml
│   │   ├── frontend-service.yaml
│   │   ├── api-deployment.yaml
│   │   ├── api-service.yaml
│   │   ├── redis-deployment.yaml
│   │   ├── redis-service.yaml
│   │   └── configmap.yaml
│   ├── storage/
│   │   ├── storageclass.yaml
│   │   ├── redis-pv.yaml
│   │   └── redis-pvc.yaml
│   └── monitoring/
│       ├── prometheus-rbac.yaml
│       ├── prometheus-config.yaml
│       ├── prometheus-deployment.yaml
│       ├── prometheus-service.yaml
│       ├── grafana-secret.yaml.example
│       ├── grafana-deployment.yaml
│       ├── grafana-service.yaml
│       └── node-exporter.yaml
└── application/             # App source code
    ├── frontend/
    │   ├── app.py
    │   ├── requirements.txt
    │   └── Dockerfile
    └── api/
        ├── app.py
        ├── requirements.txt
        └── Dockerfile
```

## Key Learnings

**Networking:**
- Private subnets use NAT Gateway for outbound internet access
- Security groups are stateful
- Pod CIDR, Service CIDR, and VPC CIDR must not overlap

**Kubernetes:**
- Control plane can go down, running pods survive (kubelet manages them locally)
- Services provide stable DNS names; without them, pods can't find each other
- Labels and selectors must match exactly
- RBAC controls what ServiceAccounts can access

**Debugging:**
- `kubectl describe pod` + Events section — first check for pod issues
- `kubectl get endpoints` — first check for service issues
- `kubectl logs --previous` — see logs from crashed containers
- Exit code 137 = OOMKilled (memory limit exceeded)

## Failure Scenarios Tested

| Scenario | What Happened | Recovery |
|----------|---------------|----------|
| Node failure | Pods rescheduled after 5 min | Automatic |
| Bad image deploy | Old pods kept running | `kubectl rollout undo` |
| Service deleted | Pods running but unreachable | Recreate service |
| Memory exceeded | Pod killed (OOMKilled) | Fix resource limits |
| Label mismatch | Service has no endpoints | Align labels |

## Running This Project

**Prerequisites:**
- AWS account with credentials configured
- Terraform installed
- Docker installed
- kubectl installed

**Deploy infrastructure:**
```bash
cd infrastructure
terraform init
terraform apply
```

**Install Kubernetes:**
SSH to control plane and run kubeadm init, then join workers.

**Deploy application:**
```bash
kubectl apply -f kubernetes/storage/
kubectl apply -f kubernetes/app/
kubectl create namespace monitoring
kubectl apply -f kubernetes/monitoring/
```

## Cost

Running costs approximately $0.17/hour:
- 3x c7i-flex.large instances (Free Tier eligible)
- NAT Gateway (~$0.045/hr)
- ALB (~$0.02/hr)

Stop instances when not in use to save costs.

## Related Blog Post

[I Built a Kubernetes Cluster from Scratch and Broke It on Purpose](#) — Detailed write-up of mistakes made and lessons learned.