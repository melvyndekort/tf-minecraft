variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID"
  type        = string
}

variable "efs_id" {
  description = "EFS file system ID"
  type        = string
}

variable "efs_security_group_id" {
  description = "EFS security group ID"
  type        = string
}

variable "ec2_key_name" {
  description = "EC2 Key Pair name"
  type        = string
}
