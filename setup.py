from setuptools import setup, find_packages

setup(
    name="robin-logger",
    version="0.2.1",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.28.0",
        "urllib3>=1.26.0",
    ],
)
