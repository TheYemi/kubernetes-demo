resource "null_resource" "cleanup_volumes" {
  triggers = {
    project_name = var.project_name
  }

  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      aws ec2 describe-volumes \
        --filters "Name=tag:Project,Values=${self.triggers.project_name}" \
        --query 'Volumes[?State==`available`].VolumeId' \
        --output text | \
      xargs -r -n1 aws ec2 delete-volume --volume-id
    EOT
  }
}