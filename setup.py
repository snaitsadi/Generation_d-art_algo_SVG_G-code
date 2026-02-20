from setuptools import setup, find_packages

setup(
    name="generative-art-ai",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'torch>=2.0.0',
        'transformers>=4.30.0',
        'datasets>=2.12.0',
        'svgwrite>=1.4.3',
        'pyserial>=3.5',
    ],
    entry_points={
        'console_scripts': [
            'artgen=main:main',
        ],
    },
)