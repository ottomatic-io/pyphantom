# coding=utf-8
from setuptools import setup, find_packages

setup(
    name="pyphantom",
    description="Phantom® highspeed camera control",
    url="http://gitlab.com/ottomatic/pyphantom",
    author="Ben Hagen",
    author_email="ben@ottomatic.io",
    install_requires=["psutil", "PyYAML", "netifaces", "cached_property", "click", "colorama"],
    packages=find_packages(),
    scripts=[],
    entry_points={"console_scripts": ["pfs_cam = pyphantom.cli.pfs_cam:cli"]},
    use_scm_version=True,
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest", "tempdir", "pcapy"],
)
