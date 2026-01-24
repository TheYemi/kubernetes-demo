output "control_plane_instance_id" {
  description = "ID of control plane Instance"
  value       = aws_instance.control-plane.id
}

output "worker_instance_ids" {
  description = "IDs of worker Instance"
  value       = aws_instance.worker[*].id
}

output "control_plane_private_ip" {
  description = "Private IP of control plane"
  value       = aws_instance.control-plane.private_ip
}

output "worker_private_ips" {
  description = "Private IPs of worker nodes"
  value       = aws_instance.worker[*].private_ip
}

output "alb_dns_name" {
  description = "ALB DNS name to access frontend"
  value       = aws_lb.k8s_alb.dns_name
}

output "ansible_ssm_bucket" {
  value = aws_s3_bucket.ansible_ssm.id
}

resource "local_file" "ansible_vars" {
  content = yamlencode({
    ansible_aws_ssm_bucket_name = aws_s3_bucket.ansible_ssm.id
    pod_network_cidr            = "10.244.0.0/16"
    kubernetes_version          = "1.29"
  })
  filename = "${path.module}/../ansible/group_vars/all/terraform_vars.yaml"
}