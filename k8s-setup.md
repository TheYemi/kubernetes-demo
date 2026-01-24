# Kubernetes Cluster Setup Guide

Manual installation steps for a kubeadm cluster on Ubuntu 22.04.

## Prerequisites

- 3 EC2 instances running Ubuntu 22.04
- Instances can communicate with each other (security group configured)
- SSM Session Manager or SSH access to all nodes

## Node Information

| Role | Private IP | Hostname |
|------|------------|----------|
| Control Plane | <control-plane-ip> | <control-plane-ip> |
| Worker 1 | <worker-1-ip> | <worker-1-ip> |
| Worker 2 | <worker-2-ip> | <worker-2-ip> |

### Please Note:

<control-plane-ip>, <worker-1-ip> and <worker-2-ip> are IP placeholders for IPs from my deployment defined in the terraform/variables.tf file (You can set your desired IPs here or leave as is, whichever works fine). 
---

## Part 1: All Nodes

Run these steps on **all three nodes** (control plane and both workers).

### 1.1 Load Kernel Modules
```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

**Why:** 
- `overlay` — enables overlay filesystem for container image layers
- `br_netfilter` — allows iptables to see bridged traffic for pod networking

### 1.2 Configure Kernel Parameters
```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sudo sysctl --system
```

**Why:**
- `bridge-nf-call-iptables` — apply firewall rules to bridged traffic
- `ip_forward` — allow node to forward packets between pods on different nodes

### 1.3 Install containerd
```bash
sudo apt-get update
sudo apt-get install -y containerd
```

### 1.4 Configure containerd
```bash
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
```

**Why:** Sets `SystemdCgroup = true` so containerd and kubelet use the same cgroup driver.

### 1.5 Install Kubernetes Components
```bash
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

**Why:** `apt-mark hold` prevents accidental upgrades — Kubernetes versions should be upgraded deliberately.

### 1.6 Disable Swap
```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

**Why:** Kubernetes requires swap to be disabled for predictable performance.

### 1.7 Verify
```bash
kubeadm version
sudo systemctl status containerd
free -h  # Swap should show 0B
```

---

## Part 2: Control Plane Only

Run these steps on the **control plane node only**.

### 2.1 Initialize the Cluster
```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

**Why:** `--pod-network-cidr=10.244.0.0/16` defines the IP range for pods. This matches Flannel's default.

**Save the output!** It contains the `kubeadm join` command for workers.

### 2.2 Configure kubectl
```bash
mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

### 2.3 Verify Control Plane
```bash
kubectl get nodes
```

Node will show `NotReady` — this is expected until CNI is installed.

### 2.4 Install Flannel CNI
```bash
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
```

### 2.5 Verify CNI
```bash
kubectl get nodes
```

Node should now show `Ready`.
```bash
kubectl get pods -n kube-flannel
kubectl get pods -n kube-system
```

All pods should be `Running`.

---

## Part 3: Worker Nodes Only

Run these steps on **both worker nodes**.

### 3.1 Join the Cluster

Use the join command from `kubeadm init` output:
```bash
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

If you lost the command, regenerate it on the control plane:
```bash
kubeadm token create --print-join-command
```

### 3.2 Verify (from Control Plane)
```bash
kubectl get nodes
```

All three nodes should show `Ready`.

---

## Part 4: Verification

Run from the control plane:
```bash
# All nodes ready
kubectl get nodes

# System pods running
kubectl get pods -A

# Test pod scheduling
kubectl run nginx-test --image=nginx --restart=Never
kubectl get pods -o wide
kubectl delete pod nginx-test
```

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Node stuck NotReady | `kubectl describe node <name>` — check conditions |
| Pods stuck Pending | `kubectl describe pod <name>` — check events |
| CNI not working | `kubectl get pods -n kube-flannel` — flannel pods running? |
| Join command expired | `kubeadm token create --print-join-command` on control plane |
| containerd not running | `sudo systemctl status containerd` |

---

## Next Steps

After cluster is running:
1. Deploy storage: `kubectl apply -f kubernetes/storage/`
2. Deploy application: `kubectl apply -f kubernetes/app/`
3. Deploy monitoring: `kubectl apply -f kubernetes/monitoring/`