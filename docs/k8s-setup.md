# Kubernetes Cluster Setup Guide

This guide covers both automated (Ansible) and manual installation of a kubeadm cluster on Ubuntu 22.04.

## Prerequisites

- 3 EC2 instances running Ubuntu 22.04
- Instances can communicate with each other (security group configured)
- SSM Session Manager access to all nodes
- AWS CLI configured with appropriate credentials

---

## Option A: Automated Setup (Recommended)

### Prerequisites for Automation

On your local machine (WSL if on Windows):

```bash
# Install Ansible
apt update && apt install -y ansible

# Install required collections and dependencies
ansible-galaxy collection install amazon.aws community.aws
pip install boto3 botocore --break-system-packages

# Install SSM Session Manager plugin
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb

# Configure AWS credentials
aws configure
```

### Deploy Infrastructure

```bash
cd infrastructure
terraform init
terraform apply
```

Wait 2 minutes for SSM agent to register instances.

### Verify Instances Are Ready

```bash
aws ssm describe-instance-information --region us-east-1 \
  --query 'InstanceInformationList[*].[InstanceId,PingStatus]' --output table
```

All instances should show `Online`.

### Run Ansible Playbook

```bash
cd ansible
ansible-playbook site.yaml
```

This will:
1. Install containerd, kubeadm, kubelet, kubectl on all nodes
2. Initialize the control plane with Canal CNI (Flannel + Calico)
3. Join worker nodes to the cluster
4. Deploy storage, application, monitoring, and network policies

### Verify Cluster

```bash
aws ssm start-session --target <control-plane-instance-id> --region us-east-1
kubectl get nodes
kubectl get pods -A
```

---

## Option B: Manual Setup

Use this if you want to understand each step or if Ansible isn't available.

### Node Information

| Role | Private IP | Hostname |
|------|------------|----------|
| Control Plane | <control-plane-ip> | <control-plane-hostname> |
| Worker 1 | <worker-1-ip> | <worker-1-hostname> |
| Worker 2 | <worker-2-ip> | <worker-2-hostname> |

---

### Part 1: All Nodes

Run these steps on **all three nodes** (control plane and both workers).

#### 1.1 Load Kernel Modules

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
- `br_netfilter` — makes bridge traffic visible to iptables for pod networking

#### 1.2 Configure Kernel Parameters

```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF

sudo sysctl --system
```

#### 1.3 Install containerd

```bash
sudo apt-get update
sudo apt-get install -y containerd
```

#### 1.4 Configure containerd

```bash
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
```

#### 1.5 Install Kubernetes Components

```bash
sudo apt-get install -y apt-transport-https ca-certificates curl gpg

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
```

#### 1.6 Install ACL (required for Ansible become_user)

```bash
sudo apt-get install -y acl
```

#### 1.7 Disable Swap

```bash
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab
```

#### 1.8 Verify

```bash
kubeadm version
sudo systemctl status containerd
free -h  # Swap should show 0B
```

---

### Part 2: Control Plane Only

Run these steps on the **control plane node only**.

#### 2.1 Initialize the Cluster

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

**Save the output!** It contains the `kubeadm join` command for workers.

#### 2.2 Configure kubectl

```bash
mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

#### 2.3 Install Canal CNI (Flannel + Calico)

```bash
curl https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/canal.yaml -O
kubectl apply -f canal.yaml
```

**Why Canal?** 
- Flannel handles pod networking (routing traffic between nodes)
- Calico handles Network Policy enforcement (pod-to-pod traffic restrictions)
- Canal combines both in a single installation

#### 2.4 Verify CNI

```bash
kubectl get nodes  # Should show Ready
kubectl get pods -n kube-system | grep -E "canal|calico"
```

---

### Part 3: Worker Nodes Only

Run these steps on **both worker nodes**.

#### 3.1 Join the Cluster

Use the join command from `kubeadm init` output:

```bash
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

If you lost the command, regenerate it on the control plane:

```bash
kubeadm token create --print-join-command
```

#### 3.2 Verify (from Control Plane)

```bash
kubectl get nodes
```

All three nodes should show `Ready`.

---

### Part 4: Deploy Application Stack

From the control plane:

```bash
# Storage
kubectl apply -f kubernetes/storage/

# Application
kubectl apply -f kubernetes/app/

# Monitoring
kubectl create namespace monitoring
kubectl apply -f kubernetes/monitoring/

# Network Policies
kubectl apply -f kubernetes/network-policies/
```

---

### Part 5: Verification

```bash
# All nodes ready
kubectl get nodes

# All pods running
kubectl get pods -A

# Network policies active
kubectl get networkpolicy

# Test application
curl http://<alb-dns>
```

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Node stuck NotReady | `kubectl describe node <n>` — check conditions |
| Pods stuck Pending | `kubectl describe pod <n>` — check events |
| CNI not working | `kubectl get pods -n kube-system` — canal pods running? |
| Join command expired | `kubeadm token create --print-join-command` |
| containerd not running | `sudo systemctl status containerd` |
| Network Policy not enforcing | Verify Canal/Calico pods are running |
| SSM connection issues | Check IAM role has SSM permissions |

---

## Cost Management

When not using the cluster:

```bash
# Stop instances (keeps EBS volumes)
aws ec2 stop-instances --instance-ids <ids> --region us-east-1

# Or destroy everything (recommended for learning)
cd infrastructure
terraform destroy
```

**Note:** NAT Gateway and ALB cost money even when instances are stopped. Use `terraform destroy` to eliminate all costs.