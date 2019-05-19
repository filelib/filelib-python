import setuptools


with open('README.md') as f:
    long_description = f.read()


setuptools.setup(
    name="filelibpy",
    version="0.0.7",
    scripts=["bin/filelib"],
    author="filelib",
    author_email="",
    description="Filelib official python package for Filelib API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/filelib/filelib-python",
    packages=setuptools.find_packages(),
    install_requires=[
        "requests==2.21.0",
        "PyJWT==1.7.1",
        "pytz==2019.1"
    ],
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ]
)
