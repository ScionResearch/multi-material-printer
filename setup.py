from setuptools import setup, find_packages

setup(
    name='scion-mmu-controller',
    version='0.1.0',
    description='Scion Multi-Material Printer Controller',
    author='Scion Research',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[],  # dependencies resolved via requirements.txt
    python_requires='>=3.8',
)
