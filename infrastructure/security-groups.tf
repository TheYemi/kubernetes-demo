resource "aws_security_group" "k8s_nodes" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-nodes-sg"
  }
}

resource "aws_security_group_rule" "k8s_nodes_self" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  security_group_id        = aws_security_group.k8s_nodes.id
  source_security_group_id = aws_security_group.k8s_nodes.id
}

resource "aws_security_group_rule" "k8s_nodes_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.k8s_nodes.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "alb_to_ingress" {
  type                     = "ingress"
  from_port                = 30080
  to_port                  = 30080
  protocol                 = "tcp"
  security_group_id        = aws_security_group.k8s_nodes.id
  source_security_group_id = aws_security_group.alb_sg.id
}