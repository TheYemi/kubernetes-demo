resource "aws_iam_role" "k8s_node_role" {
  name = "${var.project_name}-k8s-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-k8s-node-role"
  }
}

resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.k8s_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "k8s_node_profile" {
  name = "${var.project_name}-k8s-node-role-profile"
  role = aws_iam_role.k8s_node_role.name

  tags = {
    Name = "${var.project_name}-iam"
  }

}

resource "aws_iam_role_policy" "ansible_s3_access" {
  name = "${var.project_name}-ansible-s3-access"
  role = aws_iam_role.k8s_node_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.ansible_ssm.arn,
          "${aws_s3_bucket.ansible_ssm.arn}/*"
        ]
      }
    ]
  })
}