from setuptools import setup, find_packages

setup(
    name="Charts",
    version="0.1.1",
    packages=find_packages(include=["Charts", "Charts.*"]),
    include_package_data=True,
    install_requires=[
        'psycopg2-binary',
        'requests',
        'flask',
        'fastapi==0.95.1',
        'uvicorn[standard]==0.21.1',
        'asyncio==3.4.3',
        'websockets==10.4',
        'pandas',
        'numpy',
        'pytz==2023.3',
        'loguru==0.7.0',
        'httpx'
    ],
    python_requires='>=3.7',
)
