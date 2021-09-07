#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from k8s_the_hard_way_aws_cdk.k8s_the_hard_way_aws_cdk_stack import (
    K8STheHardWayAwsCdkStack,
)


app = cdk.App()
K8STheHardWayAwsCdkStack(
    app,
    "K8STheHardWayAwsCdkStack",
)

app.synth()
