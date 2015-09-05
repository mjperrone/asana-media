variable "config" {
    default = {
        vpc_id = "vpc-b91664dc"
        key_name = "mperrone"
        ami = "ami-21233111"
        app_name = "asana-media"
    }
}

provider "aws" {
    region = "us-west-2"
}

resource "aws_instance" "server" {
    ami = "${var.config.ami}"
    instance_type = "t2.micro"
    security_groups = ["${aws_security_group.allow_http.name}"]
    key_name = "${var.config.key_name}"

    tags {
        Name = "${var.config.app_name}"
    }
}


resource "aws_elb" "elb" {
    name = "${var.config.app_name}"
    availability_zones = ["us-west-2a", "us-west-2b", "us-west-2c"]
    instances = ["${aws_instance.server.id}"]

    listener {
        instance_port = 80
        instance_protocol = "http"
        lb_port = 80
        lb_protocol = "http"
    }

    health_check {
        healthy_threshold = 2
        unhealthy_threshold = 4
        timeout = 3
        target = "HTTP:80/health"
        interval = 30
    }

    cross_zone_load_balancing = true
    idle_timeout = 400
    connection_draining = true
    connection_draining_timeout = 400

    tags {
        Name = "${var.config.app_name}"
    }
}

output "elb_dns" {
    value = "${aws_elb.elb.dns_name}"
}

output "server_ip" {
    value = "${aws_instance.server.public_ip}"
}
