#!/bin/bash
yum update -y
yum install -y amazon-efs-utils

# Create mount point
mkdir -p /mnt/efs

# Mount EFS
echo "${efs_id}.efs.${region}.amazonaws.com:/ /mnt/efs efs defaults,_netdev 0 0" >> /etc/fstab
mount -a

# Set permissions for ec2-user
chown ec2-user:ec2-user /mnt/efs
chmod 755 /mnt/efs
