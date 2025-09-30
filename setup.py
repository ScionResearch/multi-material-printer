from setuptools import setup, find_packages
from pathlib import Path

def load_requirements():
    req_file = Path(__file__).parent / 'requirements.txt'
    if not req_file.exists():
        return []
    lines = []
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        lines.append(line)
    return lines

setup(
    name='scion-mmu-controller',
    version='0.2.0',
    description='Scion Multi-Material Printer Controller',
    author='Scion Research',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=load_requirements(),
    python_requires='>=3.8',
)
