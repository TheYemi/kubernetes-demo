# Monitoring Stack

## Components

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notification
- **Loki**: Log aggregation
- **Fluent Bit**: Log collection from all nodes
- **Node Exporter**: Host metrics
- **kube-state-metrics**: Kubernetes object metrics

## Network Policy Decision

Network policies are **intentionally not applied** to the monitoring namespace.

**Rationale:**
- System-level observability components require broad cluster access to scrape metrics and collect logs
- Restricting their network access creates operational complexity without meaningful security benefit
- Defense-in-depth is enforced at the application layer (see dev/staging/prod namespace policies)
- This follows production patterns where platform/system namespaces have relaxed policies

**Security is still enforced via:**
- Pod Security Standards (baseline enforcement)
- Kyverno policies (resource limits, probes, non-root where appropriate)
- RBAC for service accounts
- Application-layer network policies in dev/staging/prod namespaces

For strict application workload policies, see `kubernetes/overlays/{dev,staging,prod}/network-policy.yaml`.
