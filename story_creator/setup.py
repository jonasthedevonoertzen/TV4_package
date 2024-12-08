# story_creator/setup.py

from setuptools import setup, find_packages

setup(
    name='story_creator',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'sqlalchemy',
        'fpdf',
    ],
    author='Your Name',  # Replace with your actual name.
    author_email='your.email@example.com',  # Replace with your actual email.
    description='A package for creating and managing stories with units.',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
