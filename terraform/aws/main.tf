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
set -eux
exec > >(tee -a /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
yum update -y
yum install -y python3-pip
pip3 install --no-cache-dir flask

cat >/root/app.py <<'PY'
from flask import Flask, jsonify
import socket, os
app = Flask(__name__)
@app.get("/")
def root():
    return jsonify(ok=True, cloud=os.getenv("CLOUD","aws"), host=socket.gethostname(), message="hello from AWS")
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
PY

# create a simple systemd service so it survives reboots
cat >/etc/systemd/system/hello-api.service <<'UNIT'
[Unit]
Description=Hello API
After=network-online.target
Wants=network-online.target

[Service]
Environment=CLOUD=aws
ExecStart=/usr/bin/python3 /root/app.py
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now hello-api.service

# show listeners to confirm 0.0.0.0:8080 is up
ss -ltnp || true
EOF

  tags = { Name = "multi-cloud-instance" }
}
output "public_ip" { value = aws_instance.web.public_ip }
output "service_url" { value = "http://${aws_instance.web.public_ip}:8080/" }