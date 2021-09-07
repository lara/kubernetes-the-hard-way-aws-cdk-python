import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="k8s_the_hard_way_aws_cdk",
    version="0.0.1",
    description="Kubernetes The Hard Way — AWS CDK Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="lara",
    package_dir={"": "k8s_the_hard_way_aws_cdk"},
    packages=setuptools.find_packages(where="k8s_the_hard_way_aws_cdk"),
    install_requires=[
        "aws-cdk.core==1.119.0",
    ],
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
