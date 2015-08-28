variable "config" {
    default = {
        vpc_id = "vpc-b91664dc"
        key_name = "mperrone"
    }
}

provider "aws" {
    region = "us-west-2"
}

resource "aws_security_group" "allow_all" {
    name = "allow_all"
    description = "Allow all inbound traffic"
    vpc_id = "${var.config.vpc_id}"

    ingress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }
}

resource "aws_instance" "server" {
    ami = "ami-17928327"
    instance_type = "t2.micro"
    security_groups = ["${aws_security_group.allow_all.name}"]
    key_name = "${var.config.key_name}"

    tags {
        Name = "HelloWorld"
    }
}

output "ip" {
    value = "${aws_instance.server.public_ip}"
}

output "secid" {
    value = "${aws_security_group.allow_all.id}"
}
