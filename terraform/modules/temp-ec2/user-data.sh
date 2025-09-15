#!/bin/bash
yum update -y
yum install -y amazon-efs-utils

# Create mount point
mkdir -p /mnt/efs

# Mount EFS
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
echo "${efs_id}.efs.$REGION.amazonaws.com:/ /mnt/efs efs defaults,_netdev" >> /etc/fstab
mount -a

# Set permissions for ec2-user
chown ec2-user:ec2-user /mnt/efs
chmod 755 /mnt/efs
