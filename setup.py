from setuptools import setup, find_packages

setup(
    name="Orpheus",             # Orpheus: An application to write a harmonious symphony of fianncial data
    version="0.1.0",            # Package version
    packages=find_packages(),   
    include_package_data=True,  
    install_requires=[          # List any dependencies here
        'psycopg2-binary',
        'requests',
        'flask',
        'fastapi==0.95.1',  # FastAPI for building web APIs
        'uvicorn[standard]==0.21.1',  # ASGI server to run FastAPI apps
        'asyncio==3.4.3',  # Asynchronous I/O framework
        'websockets==10.4',  # WebSocket support for asyncio
        'pandas',  # Data manipulation and analysis library
        'numpy',  # Numerical computing library
        'pytz==2023.3',  # Timezone handling
        'loguru==0.7.0', 
        'httpx'  # Optional: for structured and easy-to-use loggi# PostgreSQL database adapter
            ],    python_requires='>=3.7',  # Minimum Python version required
)
