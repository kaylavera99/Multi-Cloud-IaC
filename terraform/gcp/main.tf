terraform {

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
  }
}

variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources in"
  default     = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = "${var.region}-a"
}

resource "google_compute_firewall" "allow_22_8080" {
  name        = "mc-allow-22-8080"
  network     = "default"
  target_tags = ["mc-web"]

  allow {
    protocol = "tcp"
    ports    = ["22", "8080"]
  }

  source_ranges = ["0.0.0.0/0"]

}

resource "google_compute_instance" "web" {
  name         = "mc-web"
  machine_type = "e2-micro"
  zone         = "${var.region}-a"

  tags = ["mc-web"]

  boot_disk {
    initialize_params {
      image = "projects/debian-cloud/global/images/family/debian-12"
    }
  }

  network_interface {
    network = "default"

    access_config {
      // Ephemeral public IP
    }
  }

  metadata_startup_script = file("${path.module}/startup.sh")

}

output "service_url" {
  value = "http://${google_compute_instance.web.network_interface[0].access_config[0].nat_ip}:8080/"

}