from setuptools import find_packages, setup

setup(
    name="boozehound",
    version="0.1",
    packages=find_packages(where="src", exclude=('tests*',)),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
       'requests',
       'pydantic',
       'pymysql',
       'tqdm',
       'python-dateutil',
       'flask'
    ],
    # pip install -e .[dev]
    extras_require={
        "dev": [
            'pylint',
            'autopep8'
        ],
    },
)
