resource "aws_lb" "k8s_alb" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name = "${var.project_name}-alb"
  }
}

resource "aws_security_group" "alb_sg" {
  name   = "${var.project_name}-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 9093
    to_port     = 9093
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

resource "aws_lb_target_group" "frontend" {
  name     = "${var.project_name}-frontend-tg"
  port     = 30080
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/health"
    port                = "30080"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-frontend-tg"
  }
}

resource "aws_lb_target_group_attachment" "worker1" {
  target_group_arn = aws_lb_target_group.frontend.arn
  target_id        = aws_instance.worker[0].id
  port             = 30080
}

resource "aws_lb_target_group_attachment" "worker2" {
  target_group_arn = aws_lb_target_group.frontend.arn
  target_id        = aws_instance.worker[1].id
  port             = 30080
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.k8s_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_target_group" "grafana" {
  name     = "${var.project_name}-grafana-tg"
  port     = 30030
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/api/health"
    port                = "30030"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-grafana-tg"
  }
}

resource "aws_lb_target_group_attachment" "grafana_worker1" {
  target_group_arn = aws_lb_target_group.grafana.arn
  target_id        = aws_instance.worker[0].id
  port             = 30030
}

resource "aws_lb_target_group_attachment" "grafana_worker2" {
  target_group_arn = aws_lb_target_group.grafana.arn
  target_id        = aws_instance.worker[1].id
  port             = 30030
}

resource "aws_lb_listener" "grafana" {
  load_balancer_arn = aws_lb.k8s_alb.arn
  port              = 3000
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.grafana.arn
  }
}

resource "aws_lb_target_group" "prometheus" {
  name     = "${var.project_name}-prometheus-tg"
  port     = 30090
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/api/health"
    port                = "30090"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-prometheus-tg"
  }
}

resource "aws_lb_target_group_attachment" "prometheus_worker1" {
  target_group_arn = aws_lb_target_group.prometheus.arn
  target_id        = aws_instance.worker[0].id
  port             = 30090
}

resource "aws_lb_target_group_attachment" "prometheus_worker2" {
  target_group_arn = aws_lb_target_group.prometheus.arn
  target_id        = aws_instance.worker[1].id
  port             = 30090
}

resource "aws_lb_listener" "prometheus" {
  load_balancer_arn = aws_lb.k8s_alb.arn
  port              = 9090
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.prometheus.arn
  }
}

resource "aws_lb_target_group" "alertmanager" {
  name     = "${var.project_name}-alertmanager-tg"
  port     = 30093
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/api/health"
    port                = "30093"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-alertmanager-tg"
  }
}

resource "aws_lb_target_group_attachment" "alertmanager_worker1" {
  target_group_arn = aws_lb_target_group.alertmanager.arn
  target_id        = aws_instance.worker[0].id
  port             = 30093
}

resource "aws_lb_target_group_attachment" "alertmanager_worker2" {
  target_group_arn = aws_lb_target_group.alertmanager.arn
  target_id        = aws_instance.worker[1].id
  port             = 30093
}

resource "aws_lb_listener" "alertmanager" {
  load_balancer_arn = aws_lb.k8s_alb.arn
  port              = 9093
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.alertmanager.arn
  }
}

resource "aws_lb_target_group" "argocd" {
  name     = "${var.project_name}-argocd-tg"
  port     = 30443
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/healthz"
    port                = "30443"
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    Name = "${var.project_name}-argocd-tg"
  }
}

resource "aws_lb_target_group_attachment" "argocd_worker1" {
  target_group_arn = aws_lb_target_group.argocd.arn
  target_id        = aws_instance.worker[0].id
  port             = 30443
}

resource "aws_lb_target_group_attachment" "argocd_worker2" {
  target_group_arn = aws_lb_target_group.argocd.arn
  target_id        = aws_instance.worker[1].id
  port             = 30443
}

resource "aws_lb_listener" "argocd" {
  load_balancer_arn = aws_lb.k8s_alb.arn
  port              = 8080
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.argocd.arn
  }
}