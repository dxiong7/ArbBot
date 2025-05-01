from setuptools import setup, find_packages

setup(
    name="arbbot",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "python-dotenv",
        # Add other dependencies from requirements.txt
    ],
    python_requires=">=3.9",
)
