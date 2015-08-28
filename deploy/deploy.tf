variable "config" {
    default = {
        vpc_id = "vpc-b91664dc"
        key_name = "mperrone"
        ami = "ami-c5bdacf5"
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

output "ip" {
    value = "${aws_instance.server.public_ip}"
}
