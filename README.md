# Production-Grade Kubernetes Platform

A fully functional, production-ready Kubernetes cluster demonstrating DevOps/SRE best practices, built from scratch on AWS. This project showcases infrastructure-as-code, GitOps workflows, comprehensive observability, and security hardening.

**Note:** Some commits may appear under different GitHub accounts (TheYemi/Opeyemi99) due to Git configuration differences across development environments. Both accounts belong to me - the project is entirely my own work!

---

## Project Overview

A self-managed 3-node Kubernetes cluster running a microservices application with complete observability, security controls, and automated operations. Designed to demonstrate production-grade platform engineering skills.

**Live Environment:** Multi-environment deployment (dev/staging/prod) with separate resource quotas and network isolation.

---

## Architecture

### Infrastructure
- **Platform:** AWS EC2 (t3.medium instances)
- **Container Runtime:** containerd
- **Networking:** Calico CNI with Canal (Calico + Flannel)
- **Storage:** AWS EBS CSI Driver with dynamic provisioning
- **Node Count:** 3 (1 control plane, 2 workers)

### Application Stack
- **Frontend:** Python Flask web UI (port 5000)
- **API:** Python Flask REST API (port 5000)
- **Cache:** Redis (in-memory key-value store)
- **Architecture Pattern:** Microservices with ClusterIP services and Ingress routing

---

## Security Implementation

### Pod Security Standards
- **Baseline:** Applied cluster-wide via Pod Security Admission
- **Restricted:** Enforced in prod namespace
- Security contexts configured for all workloads (non-root, read-only filesystem, drop ALL capabilities)

### Network Policies
- Namespace isolation (dev/staging/prod separated)
- Egress controls (DNS, external APIs whitelisted)
- Ingress restrictions (only Ingress controller can reach apps)
- Default-deny policies with explicit allow rules

### Policy Enforcement (Kyverno)
- Disallow "latest" tags for containers
- Require probes (liveness/readiness) for all pods
- Enforce resource limits/requests
- Restrict privileged containers
- Validate security contexts

### Secrets Management
- External Secrets Operator with AWS Secrets Manager integration
- Automatic secret synchronization
- Secrets rotation support (configured for immediate deletion on destroy)
- No secrets stored in Git

---

## Observability Stack

### Metrics (Prometheus)
- **Scrape Targets:**
  - Node Exporter (system metrics)
  - kube-state-metrics (Kubernetes object states)
  - cAdvisor (container resource usage)
  - Kubelet (volume metrics, pod stats)
  - Application metrics (custom Flask metrics with status_code labels)

### Dashboards (Grafana)
1. **SLO Dashboard** - Multi-window multi-burn-rate alerting (Google SRE methodology)
2. **Cluster Health** - Node resources, pod states, Loki storage
3. **Application Detail** - Per-service CPU/memory/request rate/latency/error rate

### Logging (Loki + Fluent Bit)
- Centralized log aggregation from all pods
- Fluent Bit DaemonSet with Kubernetes metadata enrichment
- 48-hour retention with automatic cleanup
- Queryable via Grafana Explore (LogQL)

### Alerting (Alertmanager)
- **Infrastructure Alerts:**
  - High CPU/memory/disk usage (warning 70%, critical 85%)
  - Pod crashes and restarts
  - Node unavailability
  - Loki storage capacity
  
- **SLO Alerts:**
  - Multi-burn-rate alerting (1h, 6h, 3d windows)
  - Error budget depletion tracking
  - Critical: 2% error rate for 1h
  - Warning: 5% error rate for 6h

- **Notification:** Slack integration for all alerts

---

## GitOps & CI/CD

### GitOps (ArgoCD)
- Declarative cluster state in Git
- Automatic synchronization (self-healing enabled)
- Multi-environment overlay structure (Kustomize)
- Separate applications for each namespace

### CI/CD Pipeline (GitHub Actions)
**Workflow:**
Code Push → Build & Scan → Tag Image → Update Kustomization → ArgoCD Sync → Deploy

**Features:**
- Automatic dev/staging deployment on code changes
- Manual production deployment workflow (workflow_dispatch)
- Separate image tags for API and Frontend services
- Trivy container image scanning
- SHA-based image tagging for traceability

---

## Repository Structure

```
.
├── application/
│   ├── api/                    # Flask REST API
│   ├── frontend/               # Flask web UI
│   └── redis/                  # Redis configuration
├── infrastructure/
│   ├── main.tf                 # AWS resources (VPC, EC2, EBS)
│   ├── secrets.tf              # Secrets Manager resources
│   └── kubeadm-init.sh         # Cluster bootstrap script
├── kubernetes/
│   ├── base/                   # Base Kustomize manifests
│   │   ├── api/
│   │   ├── frontend/
│   │   └── redis/
│   ├── overlays/               # Environment-specific configs
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   ├── bootstrap/              # ArgoCD bootstrap
│   ├── monitoring/             # Prometheus/Grafana/Loki/Fluent Bit
│   ├── external-secrets/       # ESO configuration
│   ├── ingress/                # Nginx Ingress Controller
│   ├── kyverno/                # Policy engine
│   └── network-policies/       # Network isolation rules
├── tests/
│   └── load-testing/           # k6 load test scripts
└── .github/workflows/          # CI/CD pipelines
```

---

## Technology Stack

| Category | Technology |
|----------|-----------|
| **Container Orchestration** | Kubernetes 1.29 |
| **Infrastructure** | Terraform, AWS EC2, EBS |
| **GitOps** | ArgoCD |
| **Configuration Management** | Kustomize |
| **Metrics** | Prometheus, Grafana |
| **Logging** | Loki, Fluent Bit |
| **Alerting** | Alertmanager, Slack |
| **Secrets** | External Secrets Operator, AWS Secrets Manager |
| **Policies** | Kyverno |
| **Networking** | Calico, Canal CNI, Nginx Ingress |
| **Storage** | AWS EBS CSI Driver |
| **CI/CD** | GitHub Actions |
| **Load Testing** | k6 |
| **Languages** | Python (Flask) |

---

## Key Metrics & Results

### Load Testing Results (k6)
- **Sustained Load:** 30-50 req/s over 4 minutes
- **Peak Traffic:** 50 concurrent users
- **Success Rate:** 100% (zero errors)
- **Latency:** p95 < 12ms, p99 < 15ms
- **Resource Usage:** API CPU 3.4%, Frontend CPU 10%

### Observability Coverage
- 15+ Prometheus scrape targets
- 3 comprehensive Grafana dashboards
- 12+ infrastructure alerts configured
- 9 SLO alert rules (multi-window burn rates)
- Centralized logging for 40+ pods

### Security Posture
- Pod Security Standards enforced
- 10+ network policies active
- 15+ Kyverno policy rules
- Zero secrets in Git (externalized)
- All containers run non-root

---

## Skills Demonstrated

### Platform Engineering
- Self-managed Kubernetes cluster (kubeadm)
- Multi-environment architecture
- Infrastructure as Code (Terraform)
- GitOps workflows (ArgoCD)

### Site Reliability Engineering
- SLO-based alerting (error budget tracking)
- Multi-window multi-burn-rate alerts
- Comprehensive observability (metrics, logs, dashboards)
- Capacity planning (resource quotas, limits)

### DevOps
- CI/CD pipelines (GitHub Actions)
- Container security scanning (Trivy)
- Automated deployments
- Configuration management (Kustomize)

### Security
- Policy enforcement (Kyverno)
- Network isolation (Network Policies)
- Secrets management (External Secrets Operator)
- Pod Security Standards

---

## Known Limitations & Future Enhancements

### Current Limitations
- Single-region deployment (no multi-region HA)
- No disaster recovery (Velero backup/restore not implemented)
- Manual production deployments (requires workflow_dispatch)

### Planned Enhancements
- Velero for backup/restore
- Service mesh (Linkerd) for advanced traffic management
- Horizontal Pod Autoscaling based on custom metrics
- Redis Cluster (currently single-instance)
- Multi-region deployment

---

## Documentation

- **Architecture Diagram:** See `docs/architecture.md`
- **Troubleshooting Guide:** See `docs/problems.md` (30+ issues documented and resolved)
- **Setup Guide:** See `docs/setup.md`

---

## Project Highlights

- **32+ production issues debugged and documented** (see problems.txt)
- **Zero downtime deployments** through rolling updates
- **Production-grade monitoring** with Google SRE methodology
- **Comprehensive security hardening** (PSS, Network Policies, Kyverno)
- **Full GitOps implementation** with ArgoCD
- **Externalized secrets management** with automatic rotation support

---

This project is for portfolio demonstration purposes.