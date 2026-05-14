# Production Issues Encountered & Resolved

A running log of 32+ real issues I debugged while building this cluster. Each one taught me something about production Kubernetes.

---

## Infrastructure Setup Issues

### 1. Terraform state bucket configuration broke Ansible integration
**What happened:** The terraform output keys were getting wrapped in quotes when passed to Ansible, breaking variable parsing.

**Root cause:** Using `yamlencode()` adds quotes around keys by default.

**Fix:** Switched from `yamlencode()` to heredoc syntax (`<<-EOT`) for clean YAML output without quoted keys.

**Also discovered:** SSM plugin needed explicit bucket config in `group_vars/all/all.yaml`, plus my default AWS region (eu-west-2) didn't match my resources (us-east-1). Updated Ansible config to use us-east-1 globally.

---

### 2. ArgoCD showed "Missing" and "OutOfSync" for all apps
**What happened:** No pods running in dev/staging/prod. ArgoCD couldn't find sealed secrets to decrypt.

**Root cause:** Fresh cluster = new sealing key. Old sealed secrets were encrypted with the previous cluster's key.

**Fix:** Got the kubeseal public certificate from the new cluster and re-sealed all secrets locally so ArgoCD could read them.

---

### 3. Kustomize build failed - couldn't find network policy files
**What happened:** `kustomization.yaml` referenced `api-policy` but Kustomize threw "file not found."

**Root cause:** Forgot the `.yaml` extension on the filename. It was just `api-policy` instead of `api-policy.yaml`.

**Fix:** Added `.yaml` extension. Seems obvious now but cost me 20 minutes of confusion.

---

## Application Security Context Issues

### 4. Redis pod wouldn't start - "container has runAsNonRoot and image will run as root"
**What happened:** Redis official image runs as root by default, but our security context had `runAsNonRoot: true`.

**Fix:** Removed `runAsNonRoot` from Redis deployment since Redis needs root for certain operations. Compensated with other security controls (capabilities drop, seccomp profile).

---

### 5. YAML indentation issue after fixing Redis
**What happened:** After removing `runAsNonRoot`, the pod still wouldn't start. Error changed to "invalid YAML."

**Root cause:** When I deleted the `runAsNonRoot` line, I also accidentally deleted the `securityContext:` key, misaligning the `allowPrivilegeEscalation` indentation.

**Fix:** Re-added the `securityContext:` key and realigned indentation. YAML is unforgiving.

---

### 6. Redis failed Pod Security Standards in staging/prod
**What happened:** Staging and prod use `restricted` PSS policy (stricter than dev's `baseline`). Redis pod was rejected on creation.

**Root cause:** Missing security context fields required by restricted policy.

**Fix:** Added comprehensive security hardening:
- `capabilities: drop: [ALL]` - removed all Linux capabilities
- `seccompProfile: {type: RuntimeDefault}` - restricted syscalls to reduce attack surface
- `fsGroup: 999` in pod-level securityContext - gave non-root user (UID 999) write access to EBS volume mounted as root

**Learned:** EBS volumes mount as owned by root (UID 0). Non-root containers can't write to them without `fsGroup`.

---

### 7. Duplicate serviceAccountName syntax
**What happened:** Deployment had `serviceAccountName` defined twice in the same manifest.

**Fix:** Removed duplicate line. Not sure how that even got there.

---

### 8. Frontend and API pods stuck in CreateContainerConfigError
**What happened:** Same restricted PSS issue as Redis, but for app containers.

**Fix:** Added `capabilities: drop: [ALL]` and `seccompProfile: {type: RuntimeDefault}` to both frontend and API deployments.

**Pattern recognized:** Whenever moving to restricted PSS, these two fields are mandatory.

---

## CI/CD & Security Scanning

### 9. No SAST scanning in CI/CD pipeline
**What happened:** Realized we were building and deploying code with zero static security analysis.

**Fix:** Added Trivy scanning to GitHub Actions workflow to catch vulnerabilities, SQL injection risks, and container image CVEs before deployment.

**Bonus:** Trivy immediately caught a Server-Side Template Injection (SSTI) vulnerability in the Flask templates. Fixed before it ever hit production.

---

## Service Mesh Experiment (Abandoned)

### 10. Linkerd required privileged PSS but violated security policies
**What happened:** Wanted to add Linkerd service mesh for mTLS and observability, but Linkerd needs `privileged` Pod Security Standard to inject sidecars.

**Tradeoff analysis:** 
- Gain: mTLS between services, advanced traffic routing, distributed tracing
- Cost: Weaken security posture by allowing privileged containers

**Decision:** Abandoned Linkerd. The security exposure outweighed the benefits for this project. Stuck with native Kubernetes networking.

---

### 11. Linkerd resource quota issues
**What happened:** Before abandoning Linkerd entirely, hit resource quota limits in the `linkerd` namespace.

**Fix (abandoned anyway):** Would have needed to specify explicit resource requests/limits for all Linkerd components. Didn't bother since we dropped the service mesh.

---

## Secrets Management Migration

### 12. Sealed Secrets key loss on cluster rebuilds
**What happened:** Every time I tore down and rebuilt the cluster, I had to re-seal all secrets because the new cluster generated a new sealing key.

**Pain point:** Couldn't back up the master key easily. Manual re-sealing on every rebuild was tedious.

**Led to:** Decision to migrate to External Secrets Operator + AWS Secrets Manager (see #28).

---

## Monitoring & Observability Issues

### 13. Fluent Bit wouldn't ship logs to Loki
**What happened:** Loki was running healthy, but Grafana showed zero logs. Fluent Bit pods were running but silent.

**Root cause (later discovered):** Missing `/var/log/pods` volume mount. Container runtimes use symlinks between `/var/log/containers` and `/var/log/pods`. Without both mounts, Fluent Bit couldn't tail log files.

**Fix:** Added `varpodlogs` volumeMount to Fluent Bit DaemonSet (see #19).

---

### 14. kube-state-metrics couldn't reach API server
**What happened:** Prometheus had no cluster-level metrics (pod counts, deployment status, node states).

**Root cause:** Network policy was blocking kube-state-metrics from reaching the Kubernetes API server.

**Fix:** Updated network policies to allow monitoring namespace egress to API server (see #20-21).

---

### 15. Redis PVC and Ingress wouldn't sync in ArgoCD
**What happened:** ArgoCD showed `redis-pvc` and `ingress` resources as "Unknown" or "Missing."

**Root cause:** Namespace mismatch. Manifests referenced `production` but the actual namespace was `prod`.

**Fix:** Updated all manifests to use `prod` consistently. Small typo, big impact.

---

### 16. Fluent Bit degraded in ArgoCD due to policy violations
**What happened:** Fluent Bit DaemonSet violated the `require-run-as-nonroot` Kyverno policy.

**Root cause:** System components like Fluent Bit require root to read host log files from `/var/log`.

**Fix:** Exempted `monitoring` namespace from the nonroot policy. This follows production patterns where platform namespaces get elevated privileges while app namespaces stay restricted.

**Learned:** Security policies can't be one-size-fits-all. Observability infrastructure needs different controls than application workloads.

---

### 17. Fluent Bit crash-looping with "read-only filesystem" error
**What happened:** Pod logs showed "failed to create mount point: read-only filesystem."

**Root cause:** `readOnlyRootFilesystem: true` in securityContext prevented Fluent Bit from creating directories for volume mounts.

**Why it matters:** Fluent Bit needs writable root filesystem to mount `/var/log` and `/var/log/pods` from the host.

**Fix:** Set `readOnlyRootFilesystem: false` explicitly. The container runtime requires explicit `false` to allow writable root filesystem for mount point creation.

---

### 18. Fluent Bit still failing with "mount: operation not permitted"
**What happened:** Even after fixing read-only filesystem, mount points still weren't being created.

**Root cause:** Mounted **both** `/var/log/containers` and `/var/log/pods`, but the config only read from `/var/log/containers/*.log`. The `/var/log/pods` mount was unnecessary and caused runc to fail creating mount points.

**Fix:** Removed the unnecessary `/var/log/pods` mount. Only mount what you actually need.

**Update:** Later discovered `/var/log/pods` **was** needed because of container runtime symlinks. Re-added it properly (see #13).

---

### 19. Fluent Bit and kube-state-metrics network policy blocking API server
**What happened:** Both Fluent Bit (for Kubernetes metadata enrichment) and kube-state-metrics (for cluster state) couldn't reach the API server.

**Root cause:** Network policy egress rule had `namespaceSelector`, but the Kubernetes API server endpoint isn't a pod in a namespace - it's a Service in `default` namespace that proxies to control plane.

**Fix:** Removed `namespaceSelector` from egress rules targeting the API server. Match the Service directly, not namespaces.

---

### 20. Decided to remove network policies for monitoring entirely
**What happened:** Kept hitting edge cases where observability components needed cluster-wide access.

**Decision:** Removed network policies for `monitoring` namespace. System-level observability requires broad cluster access to scrape metrics from everywhere. Restricting it creates operational complexity without meaningful security benefit.

**Tradeoff:** Monitoring namespace is less isolated, but it's already trusted infrastructure. Risk is acceptable.

---

## GitOps Configuration Issues

### 21. ArgoCD OutOfSync for namespace and app-of-apps
**What happened:** `namespaces` app and the app-of-apps (`dev`, `staging`, `prod`) were stuck OutOfSync even after manual sync.

**Root cause:** Namespaces are already managed by the dedicated `namespaces` ArgoCD Application. Setting `createNamespace: true` in the overlay apps created resource conflicts - both apps trying to own the same namespace.

**Fix:** Removed `createNamespace: true` from overlay app definitions. Let the `namespaces` app own namespace creation.

---

### 22. Volume mount failed with "not a directory" error
**What happened:** Prometheus pod crash-looping with "error reading config: is a directory."

**Root cause:** Tried to mount individual config files using `subPath`, but `subPath` tries to create a directory when the source is a ConfigMap key.

**Fix:** Removed `subPath` entirely. Mounted the entire ConfigMap to `/config/` directory and referenced files as `/config/prometheus.yaml` in Prometheus args.

**Also fixed:** Used `.yml` and `.yaml` extensions inconsistently. Prometheus's `rule_files` config couldn't find files because of the extension mismatch. Standardized everything to `.yaml`.

---

### 23. Couldn't access Prometheus UI via browser
**What happened:** Browser showed "connection refused" when trying to reach Prometheus.

**Root cause:** Cluster deployed in private subnets with no public IPs. Used HTTPS in the URL, but the load balancer only supported HTTP.

**Fix:** Changed URL from `https://` to `http://`. Simple but easy to miss.

---

## SLO & Alerting Configuration

### 24. Health check requests inflating SLO metrics
**What happened:** Debated whether to include `/health` endpoint requests in SLO calculations.

**Tradeoff analysis:**
- **Include health checks:** Proves app is responsive, but inflates request counts and makes error rate look better than reality.
- **Exclude health checks:** Measures real user experience only, but provides less data and might miss issues that only affect probes.

**Decision:** Included health checks. More data is better for a demo project, and it does prove the app is responding.

---

### 25. Grafana couldn't query Prometheus data source
**What happened:** Grafana dashboards showed "Bad Gateway" errors when trying to load Prometheus data.

**Root cause:** Prometheus was configured with `--web.external-url=/prometheus/`, so all API paths need the `/prometheus/` prefix - even for internal calls.

**Fix:** Updated Grafana datasource config from `url: http://prometheus:9090` to `url: http://prometheus:9090/prometheus`.

**Learned:** External URL prefix affects ALL requests, not just external ones.

---

### 26. Kyverno cleanup CronJobs failing with ImagePullBackOff
**What happened:** Prometheus firing constant alerts for `kyverno-clean-reports` CronJob failures.

**Root cause:** Worker nodes are in private subnets. CronJob tried to pull `bitnami/kubectl:1.28.5` from Docker Hub, but that specific tag doesn't exist.

**Why it happened:** Workers can reach Docker Hub via NAT Gateway, but the image tag is wrong.

**Decision:** Ignored the issue. The cleanup job deletes old policy reports (nice-to-have). Core Kyverno components (admission controller, background controller) are healthy. Not worth debugging for a demo project.

---

## Secrets Management Migration (Sealed Secrets → External Secrets Operator)

### 27. Terraform destroy left secrets in "scheduled for deletion" state
**What happened:** Ran `terraform destroy`, then `terraform apply`. Got error: "secret already scheduled for deletion."

**Root cause:** AWS Secrets Manager has a 7-30 day recovery window by default. `terraform destroy` scheduled deletion but didn't immediately delete secrets.

**Fix:** Added `recovery_window_in_days = 0` to all `aws_secretsmanager_secret` resources in `secrets.tf`. Forces immediate deletion on destroy.

**Manual workaround (when needed):**
```bash
aws secretsmanager delete-secret --secret-id <name> --force-delete-without-recovery
```

---

### 28. Why I migrated from Sealed Secrets to External Secrets Operator
**Pain point:** Had to re-seal secrets every time I spun up a new cluster (see #12).

**Solution:** Migrated to External Secrets Operator + AWS Secrets Manager.

**Tradeoffs:**

| | Sealed Secrets | External Secrets Operator |
|---|---|---|
| **Storage** | Encrypted in Git | AWS Secrets Manager |
| **Cluster rebuild** | Manual re-seal required | Auto-sync from AWS |
| **Rotation** | Manual | Automatic (via Lambda + ESO) |
| **Cost** | Free | Small AWS cost (~$0.40/secret/month) |
| **Security** | Encrypted at rest in Git | Centralized secrets management |

**Decision:** Paid AWS cost is worth the automation.

---

### 29. ESO couldn't create secrets - "already exists" error
**What happened:** After deploying ESO, secrets stayed in "SecretSyncPending" state. Logs showed "secret already exists."

**Root cause:** Sealed Secrets controller still owned the existing secret resources. ESO tried to create them but couldn't take ownership.

**Fix:**
1. Removed Sealed Secrets manifests from Git
2. Removed Sealed Secrets references from all `kustomization.yaml` files
3. Deleted old secrets: `kubectl delete secret <name> -n <namespace>`
4. Let ESO recreate and own the new secrets

**Learned:** Can't have two operators managing the same resource. Clean up the old owner first.

---

## Prometheus Configuration Issues

### 30. Prometheus crash-looping with "is a directory" error
**What happened:** Prometheus pod logs: "error reading config file '/etc/prometheus/prometheus.yml': is a directory."

**Root cause:** Prometheus image has default config baked in at `/etc/prometheus/prometheus.yml`. Mounting my own ConfigMap there created a conflict. Plus I used mixed extensions (`.yml` and `.yaml`), breaking the `rule_files` pattern matching.

**Fix:**
1. Mounted all configs to `/config/` instead of `/etc/prometheus/` to avoid image defaults
2. Standardized all files to `.yaml` extension
3. Updated Prometheus args: `--config.file=/config/prometheus.yaml`
4. Updated `rule_files` paths to `- /config/alerts/*.yaml` and `- /config/rules/*.yaml`

**Learned:** Don't mount volumes over paths the container image already uses.

---

### 31. Alertmanager stuck in ContainerCreating with "secret not found"
**What happened:** Alertmanager pod wouldn't start. Event logs: "secret 'alertmanager-secret' not found."

**Root cause:** Deployment spec referenced `alertmanager-config`, but ExternalSecret created it as `alertmanager-secret`. Name mismatch.

**Fix:** Updated ExternalSecret's `target.name` from `alertmanager-secret` to `alertmanager-config` to match deployment spec. Deleted old secret, let ESO recreate.

**Learned:** Always verify secret names match between ExternalSecret definition and pod volume mounts.

---

### 32. Node Exporter only monitoring worker nodes, not control plane
**What happened:** Grafana dashboards showed metrics for 2 nodes, but cluster has 3. Control plane metrics were missing.

**Root cause:** Control plane has a `node-role.kubernetes.io/control-plane:NoSchedule` taint by default. Node Exporter DaemonSet didn't tolerate it, so no pod scheduled on control plane.

**Additional issue:** Prometheus had a relabel config that explicitly **dropped** control plane nodes from scraping.

**Fix:**
1. Added toleration to Node Exporter DaemonSet:
```yaml
tolerations:
- key: node-role.kubernetes.io/control-plane
  operator: Exists
  effect: NoSchedule
```
2. Removed the relabel config that dropped control plane nodes

**Why it matters:** Not monitoring control plane hides critical infrastructure metrics (API server load, etcd health, scheduler performance).

---

## Summary Stats

- **Total issues debugged:** 32+
- **Cluster rebuilds:** 15+ (each rebuild surfaced new issues)
- **Time spent debugging vs building:** Roughly 70/30 split
- **Most educational issue:** Network policies blocking observability which taught me when to enforce vs when to trust

**Key lesson:** Production Kubernetes is 20% knowing what to deploy, 80% debugging why it doesn't work the first time.