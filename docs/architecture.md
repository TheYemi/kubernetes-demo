# Architecture Diagrams

## Infrastructure Overview
┌─────────────────────────────────────────────────────────────────────┐
│                            AWS Cloud                                │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      VPC (10.0.0.0/16)                        │ │
│  │                                                               │ │
│  │  ┌─────────────────────┐      ┌──────────────────────────┐  │ │
│  │  │  Public Subnet      │      │   Private Subnet         │  │ │
│  │  │  (10.0.1.0/24)      │      │   (10.0.3.0/24)          │  │ │
│  │  │                     │      │                          │  │ │
│  │  │  ┌──────────────┐   │      │  ┌──────────────────┐   │  │ │
│  │  │  │ NAT Gateway  │   │      │  │ Control Plane    │   │  │ │
│  │  │  │              │   │      │  │ ip-10-0-3-146    │   │  │ │
│  │  │  └──────┬───────┘   │      │  │ - API Server     │   │  │ │
│  │  │         │           │      │  │ - etcd           │   │  │ │
│  │  │  ┌──────▼───────┐   │      │  │ - Scheduler      │   │  │ │
│  │  │  │ Internet     │   │      │  │ - Controller Mgr │   │  │ │
│  │  │  │ Gateway      │   │      │  └──────────────────┘   │  │ │
│  │  │  └──────────────┘   │      │                          │  │ │
│  │  └─────────────────────┘      │  ┌──────────────────┐   │  │ │
│  │                                │  │ Worker Node 1    │   │  │ │
│  │  ┌─────────────────────┐      │  │ ip-10-0-3-62     │   │  │ │
│  │  │  Private Subnet     │      │  │ - kubelet        │   │  │ │
│  │  │  (10.0.4.0/24)      │      │  │ - containerd     │   │  │ │
│  │  │                     │      │  │ - kube-proxy     │   │  │ │
│  │  │  ┌──────────────┐   │      │  └──────────────────┘   │  │ │
│  │  │  │ Worker Node 2│   │      │                          │  │ │
│  │  │  │ ip-10-0-4-183│   │      │  ┌──────────────────┐   │  │ │
│  │  │  │ - kubelet    │   │      │  │ EBS Volumes      │   │  │ │
│  │  │  │ - containerd │   │      │  │ - Prometheus     │   │  │ │
│  │  │  │ - kube-proxy │   │      │  │ - Grafana        │   │  │ │
│  │  │  └──────────────┘   │      │  │ - Loki (5GB)     │   │  │ │
│  │  └─────────────────────┘      │  └──────────────────┘   │  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │               AWS Secrets Manager (us-east-1)                 │ │
│  │  - grafana-admin-password                                     │ │
│  │  - redis-password                                             │ │
│  │  - alertmanager-config (Slack webhook)                        │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

**Notes:**
- 3-node cluster: 1 control plane (manages cluster state) + 2 workers (run application workloads)
- Private subnets protect nodes from direct internet access
- NAT Gateway enables worker nodes to pull container images from Docker Hub
- EBS volumes provide persistent storage for stateful components (Redis, Grafana, Loki)
- AWS Secrets Manager stores sensitive credentials outside the cluster for security
- Control plane runs Kubernetes core components: API Server (cluster entry point), etcd (distributed database), Scheduler (decides pod placement), Controller Manager (maintains desired state)

---

## Application Request Flow
                                ┌──────────────────┐
                                │   GitHub Repo    │
                                │  (Source of      │
                                │   Truth)         │
                                └────────┬─────────┘
                                         │
                                         │ Git Sync
                                         ▼
┌─────────────┐                   ┌──────────────────┐
│   Internet  │                   │     ArgoCD       │
│    User     │                   │  (GitOps Engine) │
└──────┬──────┘                   └────────┬─────────┘
│                                   │
│ HTTP Request                      │ Auto Deploy
│                                   ▼
│                          ┌─────────────────────┐
│                          │  Kustomize Overlays │
│                          │  dev/staging/prod   │
│                          └─────────┬───────────┘
│                                    │
▼                                    ▼
┌─────────────────┐            ┌──────────────────────────┐
│ Nginx Ingress   │            │   Kubernetes Cluster     │
│ Controller      │            │                          │
│ (External LB)   │            │  ┌────────────────────┐  │
└────────┬────────┘            │  │  Namespace: prod   │  │
│                     │  │                    │  │
│ Route: /            │  │  ┌──────────────┐ │  │
▼                     │  │  │  Frontend    │ │  │
┌──────────────────┐           │  │  │  (3 pods)    │ │  │
│  Frontend Service│           │  │  │  Port 5000   │ │  │
│  ClusterIP       │◄──────────┼──┼──┤  Flask App   │ │  │
└────────┬─────────┘           │  │  └──────┬───────┘ │  │
│                     │  │         │         │  │
│ /tasks              │  │         │ HTTP    │  │
│ /health             │  │         ▼         │  │
▼                     │  │  ┌──────────────┐ │  │
┌──────────────────┐           │  │  │  API Service │ │  │
│   API Service    │           │  │  │  ClusterIP   │ │  │
│   ClusterIP      │◄──────────┼──┼──┤  (3 pods)    │ │  │
└────────┬─────────┘           │  │  │  Port 5000   │ │  │
│                     │  │  └──────┬───────┘ │  │
│ Cache Read/Write    │  │         │         │  │
▼                     │  │         │ Redis   │  │
┌──────────────────┐           │  │         ▼         │  │
│  Redis Service   │           │  │  ┌──────────────┐ │  │
│  ClusterIP       │◄──────────┼──┼──┤  Redis       │ │  │
└──────────────────┘           │  │  │  (1 pod)     │ │  │
│  │  │  Port 6379   │ │  │
│  │  └──────────────┘ │  │
│  └────────────────────┘  │
│                          │
│  Network Policies:       │
│  - Default deny all      │
│  - Allow frontend → API  │
│  - Allow API → Redis     │
│  - Allow Ingress → Pods  │
└──────────────────────────┘

**Notes:**
- GitOps pattern: Git is the single source of truth; ArgoCD continuously syncs cluster state
- Kustomize overlays enable environment-specific configurations without duplicating manifests
- Nginx Ingress Controller acts as the cluster's entry point, routing external traffic to services
- Services use ClusterIP (internal-only) for pod-to-pod communication within the cluster
- Network Policies enforce zero-trust networking: default deny-all, explicit allow rules only
- Multi-environment isolation: dev/staging/prod namespaces are network-isolated from each other
- Each environment has separate resource quotas to prevent noisy-neighbor issues
---

## Observability Architecture
┌─────────────────────────────────────────────────────────────────────┐
│                      Kubernetes Cluster                             │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Application Pods                           │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │ │
│  │  │ Frontend │  │   API    │  │  Redis   │                    │ │
│  │  │          │  │          │  │          │                    │ │
│  │  │ /metrics │  │ /metrics │  │          │                    │ │
│  │  └────┬─────┘  └────┬─────┘  └──────────┘                    │ │
│  │       │             │                                         │ │
│  │       │ Expose      │ Expose                                 │ │
│  │       │ Metrics     │ Metrics                                │ │
│  │       │             │                                         │ │
│  │       │             │        Write Logs                      │ │
│  │       │             │        to stdout/stderr                │ │
│  │       │             │               │                        │ │
│  └───────┼─────────────┼───────────────┼────────────────────────┘ │
│          │             │               │                          │
│          │             │               ▼                          │
│  ┌───────▼─────────────▼────┐    ┌─────────────────────────┐     │
│  │     Prometheus           │    │  Container Runtime      │     │
│  │   (Metrics Storage)      │    │  writes to:             │     │
│  │                          │    │  /var/log/containers/   │     │
│  │  Scrapes every 15s:      │    │  /var/log/pods/         │     │
│  │  - Frontend metrics      │    └──────────┬──────────────┘     │
│  │  - API metrics           │               │                    │
│  │  - Node Exporter         │               │                    │
│  │  - kube-state-metrics    │               │ Tail logs          │
│  │  - cAdvisor              │               ▼                    │
│  │  - Kubelet               │    ┌─────────────────────────┐     │
│  │                          │    │  Fluent Bit DaemonSet   │     │
│  │  Evaluates:              │    │  (1 pod per node)       │     │
│  │  - Alert rules           │    │                         │     │
│  │  - Recording rules       │    │  - Tails log files      │     │
│  └───────┬──────────────────┘    │  - Adds k8s metadata    │     │
│          │                       │  - Ships to Loki        │     │
│          │ Query                 └──────────┬──────────────┘     │
│          │                                  │                    │
│  ┌───────▼──────────────────┐              │                    │
│  │      Grafana             │              │ HTTP POST          │
│  │   (Visualization)        │              │                    │
│  │                          │              ▼                    │
│  │  Dashboards:             │    ┌─────────────────────────┐     │
│  │  - SLO Dashboard         │    │        Loki             │     │
│  │  - Cluster Health        │    │   (Log Storage)         │     │
│  │  - Application Detail    │    │                         │     │
│  │                          │    │  - Stores logs          │     │
│  │  Data Sources:           │    │  - 48h retention        │     │
│  │  - Prometheus            │    │  - Auto compaction      │     │
│  │  - Loki                  │    │  - 5GB EBS volume       │     │
│  └──────────────────────────┘    └─────────────────────────┘     │
│          ▲                                  │                    │
│          │                                  │                    │
│          │ Query logs                       │ Query              │
│          │ (LogQL)                          │                    │
│          └──────────────────────────────────┘                    │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Alertmanager                                 │  │
│  │         (Alert Routing & Grouping)                        │  │
│  │                                                           │  │
│  │  Receives alerts from Prometheus                          │  │
│  │  Routes to Slack webhook                                  │  │
│  │                                                           │  │
│  │  Alert Groups:                                            │  │
│  │  - Infrastructure (CPU, memory, disk)                     │  │
│  │  - SLO Burn Rates (1h, 6h, 3d)                           │  │
│  │  - Pod Health (crashes, restarts)                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

**Notes:**
- Metrics collection: Prometheus scrapes endpoints every 15 seconds, storing time-series data
- Application metrics: Flask apps expose custom /metrics endpoints (request rate, latency, status codes)
- Node-level visibility: Node Exporter provides OS metrics, cAdvisor tracks container resources
- Kubernetes state: kube-state-metrics exposes cluster object status (deployments, pods, nodes)
- Log aggregation: Fluent Bit runs as DaemonSet (one pod per node), tails log files, enriches with metadata
- Loki stores logs indexed by labels (not content) for cost-efficient long-term storage
- 48-hour retention with automatic compaction prevents disk exhaustion
- Grafana provides unified interface: query metrics (PromQL) and logs (LogQL) in one place
- Alertmanager groups/routes alerts to Slack, prevents alert fatigue through deduplication

---

## Security Architecture
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │           Pod Security Admission (PSA)                    │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │ │
│  │  │  dev: │  │  staging:  │  │  prod:     │         │ │
│  │  │  baseline  │  │  baseline  │  │  restricted│         │ │
│  │  └────────────┘  └────────────┘  └────────────┘         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                  │
│                             ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Kyverno Policy Engine                        │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  Admission Policies (validate on create):           │ │ │
│  │  │  - require-probes                                   │ │ │
│  │  │  - require-resource-limits                          │ │ │
│  │  │  - disallow-privileged-containers                   │ │ │
│  │  │  - require-run-as-nonroot                           │ │ │
│  │  │  - require-drop-all-capabilities                    │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                  │
│                             ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Network Policies                             │ │
│  │                                                           │ │
│  │  Namespace Isolation:                                     │ │
│  │  ┌──────────┐      ┌──────────┐      ┌──────────┐       │ │
│  │  │   dev    │      │ staging  │      │   prod   │       │ │
│  │  │ isolated │      │ isolated │      │ isolated │       │ │
│  │  └──────────┘      └──────────┘      └──────────┘       │ │
│  │                                                           │ │
│  │  Default: Deny all ingress/egress                         │ │
│  │  Allowed:                                                 │ │
│  │  - Ingress → Frontend (port 5000)                         │ │
│  │  - Frontend → API (port 5000)                             │ │
│  │  - API → Redis (port 6379)                                │ │
│  │  - All → DNS (port 53)                                    │ │
│  │  - Monitoring → All (scrape metrics)                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                             │                                  │
│                             ▼                                  │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │        External Secrets Operator (ESO)                    │ │
│  │                                                           │ │
│  │  AWS Secrets Manager ──► ESO ──► Kubernetes Secrets      │ │
│  │                                                           │ │
│  │  Secrets:                                                 │ │
│  │  - grafana-admin-password                                 │ │
│  │  - redis-password                                         │ │
│  │  - alertmanager-config                                    │ │
│  │                                                           │ │
│  │  Sync Interval: 1h                                        │ │
│  │  Rotation Support: Enabled                                │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘

**Notes:**
- Defense in depth: multiple security layers from admission control to network isolation
- Pod Security Standards: baseline (dev/staging) allows common patterns, restricted (prod) enforces stricter controls (non-root, read-only filesystem, dropped capabilities)
- Kyverno enforces policy as code: validates workloads at admission time, blocks non-compliant resources
- Network Policies implement microsegmentation: each service can only talk to explicitly allowed endpoints
- Default deny-all stance: nothing works until explicitly permitted, reducing attack surface
- External Secrets Operator eliminates secrets in Git: credentials live in AWS Secrets Manager, synced to cluster
- Automatic rotation support: when secrets change in AWS, ESO updates Kubernetes secrets without pod restarts
- Zero secrets in source control: Git repository contains no sensitive data, safe to share publicly