import setuptools

setuptools.setup(
    name="lightning_power_users_website",
    version="0.0.0",
    author="Pierre Rochard",
    packages=setuptools.find_packages(
        exclude=['googleapis', "*.tests", "*.tests.*", "tests.*", "tests"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "grpcio",
        "grpcio-tools",
        "googleapis-common-protos"
    ],
    python_requires='>=3',
)
