import boto3

from aws_cdk import (
    core as cdk,
    aws_ec2 as ec2,
    aws_elasticloadbalancing as elb,
    aws_elasticloadbalancingv2 as elbv2,
    aws_autoscaling as autoscaling,
)

PROJECT = "kubernetes-the-hard-way"
OWNER = "lara"

DEFAULT_TAGS = {"Project": PROJECT, "Owner": OWNER}
AMI_ID = "ami-007"
SSH_KEY_PAIR = "ssh-key-pair"
WORKSTATION = "workstation-ip"

REGION = "us-west-2"
VPC_CIDR = "10.0.0.0/16"
POD_CIDR = "10.200"

# ETCD config
ETCD_MIN_CAPACITY = 3
ETCD_MAX_CAPACITY = 3
ETCD_DESIRED_CAPACITY = 3
ETCD_INSTANCE_TYPE = "t2.small"

# Controller config
CONTROLLER_MIN_CAPACITY = 3
CONTROLLER_MAX_CAPACITY = 3
CONTROLLER_DESIRED_CAPACITY = 3
CONTROLLER_INSTANCE_TYPE = "t2.small"

# Worker config
WORKER_MIN_CAPACITY = 3
WORKER_MAX_CAPACITY = 3
WORKER_DESIRED_CAPACITY = 3
WORKER_INSTANCE_TYPE = "t2.small"


def latest_ami():
    ec2_client = boto3.client("ec2", region_name=REGION)
    images_sorted_by_creation_date = sorted(
        ec2_client.describe_images(
            Filters=[{"Name": "name", "Values": ["ubuntu18.04-**"]}],
            Owners=["748666506640"],
        )["Images"],
        key=lambda image: image["CreationDate"],
        reverse=True,
    )
    return images_sorted_by_creation_date[0]["ImageId"]


class K8STheHardWayAwsCdkStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, tags=DEFAULT_TAGS, **kwargs)

        ami = ec2.GenericLinuxImage(ami_map={REGION: AMI_ID})
        vpc = ec2.Vpc(
            self,
            PROJECT,
            cidr=VPC_CIDR,
            enable_dns_hostnames=True,
            enable_dns_support=True,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    cidr_mask=24, name="private", subnet_type=ec2.SubnetType.PRIVATE
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24, name="public", subnet_type=ec2.SubnetType.PUBLIC
                ),
            ],
        )

        bastion_host = ec2.Instance(
            self,
            f"{PROJECT}-bastion",
            instance_type=ec2.InstanceType("t2.small"),
            machine_image=ec2.AmazonLinuxImage(),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_name="public"),
            key_name=SSH_KEY_PAIR,
        )

        etcd_asg = autoscaling.AutoScalingGroup(
            self,
            f"{PROJECT}-etcd",
            vpc=vpc,
            min_capacity=ETCD_MIN_CAPACITY,
            max_capacity=ETCD_MAX_CAPACITY,
            desired_capacity=ETCD_DESIRED_CAPACITY,
            instance_type=ec2.InstanceType(ETCD_INSTANCE_TYPE),
            machine_image=ami,
            # key_name=SSH_KEY_PAIR,
            vpc_subnets=ec2.SubnetSelection(subnet_name="private"),
            associate_public_ip_address=False,
        )

        controller_asg = autoscaling.AutoScalingGroup(
            self,
            f"{PROJECT}-controller",
            vpc=vpc,
            min_capacity=CONTROLLER_MIN_CAPACITY,
            max_capacity=CONTROLLER_MAX_CAPACITY,
            desired_capacity=CONTROLLER_DESIRED_CAPACITY,
            instance_type=ec2.InstanceType(CONTROLLER_INSTANCE_TYPE),
            machine_image=ami,
            # key_name=SSH_KEY_PAIR,
            vpc_subnets=ec2.SubnetSelection(subnet_name="private"),
            associate_public_ip_address=False,
        )

        worker_asg = autoscaling.AutoScalingGroup(
            self,
            f"{PROJECT}-worker",
            vpc=vpc,
            min_capacity=WORKER_MIN_CAPACITY,
            max_capacity=WORKER_MAX_CAPACITY,
            desired_capacity=WORKER_DESIRED_CAPACITY,
            instance_type=ec2.InstanceType(WORKER_INSTANCE_TYPE),
            machine_image=ami,
            # key_name=SSH_KEY_PAIR,
            vpc_subnets=ec2.SubnetSelection(subnet_name="private"),
            associate_public_ip_address=False,
        )

        controller_public_lb = elb.LoadBalancer(
            self,
            f"{PROJECT}-controller-public-lb",
            vpc=vpc,
            internet_facing=True,
            health_check=elb.HealthCheck(
                port=6443, protocol=elb.LoadBalancingProtocol.TCP
            ),
        )

        controller_private_lb = elb.LoadBalancer(
            self,
            f"{PROJECT}-controller-private-lb",
            vpc=vpc,
            internet_facing=False,
            health_check=elb.HealthCheck(
                port=6443, protocol=elb.LoadBalancingProtocol.TCP
            ),
        )

        bastion_sg = ec2.SecurityGroup(
            self,
            f"{PROJECT}-bastion-sg",
            security_group_name=f"{PROJECT}-bastion-sg",
            description=f"{PROJECT} - bastion security group",
            vpc=vpc,
            allow_all_outbound=True,
        )
        etcd_sg = ec2.SecurityGroup(
            self,
            f"{PROJECT}-etcd-sg",
            security_group_name=f"{PROJECT}-etcd-sg",
            description=f"{PROJECT} - etcd security group",
            vpc=vpc,
            allow_all_outbound=True,
        )
        worker_sg = ec2.SecurityGroup(
            self,
            f"{PROJECT}-worker-sg",
            security_group_name=f"{PROJECT}-worker-sg",
            description=f"{PROJECT} - worker security group",
            vpc=vpc,
            allow_all_outbound=True,
        )
        controller_sg = ec2.SecurityGroup(
            self,
            f"{PROJECT}-controller-sg",
            security_group_name=f"{PROJECT}-controller-sg",
            description=f"{PROJECT} - controller security group",
            vpc=vpc,
            allow_all_outbound=True,
        )
        controller_public_lb_sg = ec2.SecurityGroup(
            self,
            f"{PROJECT}-controller-public-lb-sg",
            security_group_name=f"{PROJECT}-controller-public-lb-sg",
            description=f"{PROJECT} - controller public lb security group",
            vpc=vpc,
            allow_all_outbound=True,
        )
        controller_private_lb_sg = ec2.SecurityGroup(
            self,
            f"{PROJECT}-controller-private-lb-sg",
            security_group_name=f"{PROJECT}-controller-private-lb-sg",
            description=f"{PROJECT} - controller private lb security group",
            vpc=vpc,
            allow_all_outbound=True,
        )

        bastion_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(WORKSTATION), connection=ec2.Port.tcp(22)
        )

        etcd_sg.add_ingress_rule(peer=bastion_sg, connection=ec2.Port.tcp(22))
        etcd_sg.add_ingress_rule(
            peer=controller_sg,
            connection=ec2.Port.tcp_range(start_port=2379, end_port=2380),
        )
        etcd_sg.add_ingress_rule(
            peer=etcd_sg, connection=ec2.Port.tcp_range(start_port=2379, end_port=2380)
        )

        # controller_sg.add_ingress_rule(peer=worker_sg, connection=ec2.Port.all_traffic())
        controller_sg.add_ingress_rule(peer=bastion_sg, connection=ec2.Port.tcp(22))
        controller_sg.add_ingress_rule(
            peer=controller_public_lb_sg, connection=ec2.Port.tcp(6443)
        )
        controller_sg.add_ingress_rule(
            peer=controller_private_lb_sg, connection=ec2.Port.tcp(6443)
        )
        controller_sg.add_ingress_rule(peer=worker_sg, connection=ec2.Port.tcp(6443))
        controller_public_lb_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(WORKSTATION), connection=ec2.Port.tcp(6443)
        )
        controller_public_lb_sg.add_ingress_rule(
            peer=controller_sg, connection=ec2.Port.tcp(6443)
        )
        controller_private_lb_sg.add_ingress_rule(
            peer=controller_sg, connection=ec2.Port.tcp(6443)
        )
        controller_private_lb_sg.add_ingress_rule(
            peer=worker_sg, connection=ec2.Port.tcp(6443)
        )

        worker_sg.add_ingress_rule(peer=bastion_sg, connection=ec2.Port.tcp(22))
        worker_sg.add_ingress_rule(
            peer=controller_sg, connection=ec2.Port.all_traffic()
        )

        bastion_host.add_security_group(bastion_sg)
        etcd_asg.add_security_group(etcd_sg)
        worker_asg.add_security_group(worker_sg)
        controller_asg.add_security_group(controller_sg)

        controller_public_lb.add_listener(
            external_port=6443,
            external_protocol=elb.LoadBalancingProtocol.TCP,
            allow_connections_from=[ec2.Peer().ipv4(WORKSTATION), controller_sg],
        )
        controller_private_lb.add_listener(
            external_port=6443,
            external_protocol=elb.LoadBalancingProtocol.TCP,
            allow_connections_from=[controller_sg, worker_sg],
        )
        controller_public_lb.add_target(target=controller_asg)
        controller_private_lb.add_target(target=controller_asg)

        cdk.Tag.add(
            bastion_host, apply_to_launched_instances=True, key="Name", value=PROJECT
        )
        cdk.Tag.add(
            bastion_host, apply_to_launched_instances=True, key="Owner", value=OWNER
        )
        cdk.Tag.add(
            etcd_asg, apply_to_launched_instances=True, key="Name", value=PROJECT
        )
        cdk.Tag.add(
            etcd_asg, apply_to_launched_instances=True, key="Owner", value=OWNER
        )
        cdk.Tag.add(
            worker_asg, apply_to_launched_instances=True, key="Name", value=PROJECT
        )
        cdk.Tag.add(
            worker_asg, apply_to_launched_instances=True, key="Owner", value=OWNER
        )
        cdk.Tag.add(
            controller_asg, apply_to_launched_instances=True, key="Name", value=PROJECT
        )
        cdk.Tag.add(
            controller_asg, apply_to_launched_instances=True, key="Owner", value=OWNER
        )
        cdk.Tag.add(
            controller_public_lb,
            apply_to_launched_instances=True,
            key="Name",
            value=PROJECT,
        )
        cdk.Tag.add(
            controller_public_lb,
            apply_to_launched_instances=True,
            key="Owner",
            value=OWNER,
        )
        cdk.Tag.add(
            controller_private_lb,
            apply_to_launched_instances=True,
            key="Name",
            value=PROJECT,
        )
        cdk.Tag.add(
            controller_private_lb,
            apply_to_launched_instances=True,
            key="Owner",
            value=OWNER,
        )

        for subnet in vpc.public_subnets:
            cdk.Tag.add(subnet, key="Attribute", value="public")
            cdk.Tag.add(subnet, key="Name", value=PROJECT)
            cdk.Tag.add(subnet, key="Owner", value=OWNER)

        for subnet in vpc.private_subnets:
            cdk.Tag.add(subnet, key="Attribute", value="private")
            cdk.Tag.add(subnet, key="Name", value=PROJECT)
            cdk.Tag.add(subnet, key="Owner", value=OWNER)
