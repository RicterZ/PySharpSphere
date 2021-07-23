# coding: utf-8
import codecs
from setuptools import setup, find_packages


with open('requirements.txt') as f:
    requirements = [l for l in f.read().splitlines() if l]


def long_description():
    with codecs.open('README.md', 'r') as readme:
        return readme.read()


setup(
    name='pySharpSphere',
    version='0.0.1',
    packages=find_packages(),

    author='Ricter Zheng',
    author_email='ricterzheng@gmail.com',
    keywords=['vCenter Server', 'exploit', 'SharpSphere', 'pySharpSphere'],
    description='vCenter Server attack toolkit',
    long_description=long_description(),
    url='https://github.com/RicterZ/PySharpSphere',
    download_url='https://github.com/RicterZ/PySharpSphere/tarball/main',
    include_package_data=True,
    zip_safe=False,

    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'pysharpsphere = pysharpsphere.main:main',
        ]
    },
    license='MIT',
)