from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    author="Ben Hagen",
    author_email="ben@ottomatic.io",
    description="Phantom® highspeed camera control",
    entry_points={"console_scripts": ["pfs_cam = pyphantom.cli.pfs_cam:cli"]},
    install_requires=["psutil", "PyYAML", "netifaces", "cached_property", "click", "colorama", "timeout-decorator"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    name="pyphantom",
    packages=find_packages(),
    scripts=[],
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest", "tempdir", "pcapy"],
    url="http://gitlab.com/ottomatic-io/pyphantom",
    use_scm_version=True,
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)
