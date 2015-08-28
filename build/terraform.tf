provider "aws" {
    region = "us-west-2"
}

resource "aws_instance" "server" {
    ami = "ami-17928327"
    instance_type = "t2.micro"
    tags {
        Name = "HelloWorld"
    }
}
