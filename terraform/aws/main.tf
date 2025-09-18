terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0.0"
    }
  }
}

provider "aws" {
  region = var.region

}

variable "region" {
  type    = string
  default = "us-east-1"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet" "az1" {
  vpc_id = data.aws_vpc.default.id

  filter {
    name   = "availability-zone"
    values = ["${var.region}a"]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

resource "aws_security_group" "web" {
  name        = "multi-cloud-sg"
  description = "Allow SSH 22 and app 8080"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
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
}

data "aws_ami" "amzn2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

}

resource "aws_instance" "web" {
  ami                         = data.aws_ami.amzn2.id
  instance_type               = "t3.micro"
  subnet_id                   = data.aws_subnet.az1.id
  vpc_security_group_ids      = [aws_security_group.web.id]
  associate_public_ip_address = true
  user_data_replace_on_change = true

  user_data = <<-EOF
#!/bin/bash
set -euxo pipefail
# mirror output to console + log for easy debugging
exec > >(tee -a /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

yum update -y
amazon-linux-extras install docker -y || yum install -y docker
systemctl enable --now docker
docker --version

#  tiny Flask app inside Python container 
docker run -d --restart unless-stopped --name hello-api -p 8080:8080 -e CLOUD=aws \
  python:3.11-slim bash -lc "pip install flask && python - <<'PY'
from flask import Flask, jsonify
import socket, os
app = Flask(__name__)
@app.get('/')
def r():
    return jsonify({'ok': True, 'cloud': os.getenv('CLOUD','aws'), 'host': socket.gethostname(), 'message': 'hello from AWS (docker)'})
app.run(host='0.0.0.0', port=8080)
PY"

# show containers and listeners
docker ps -a
ss -ltnp || true
EOF
}
output "public_ip" { value = aws_instance.web.public_ip }
output "service_url" { value = "http://${aws_instance.web.public_ip}:8080/" }