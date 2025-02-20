from setuptools import setup, find_packages

setup(
    name="koru",
    version="0.1",
    packages=find_packages(include=[
        'input_processing*',
        'input_classifier*',
        'webapp*',
        'shared*'
    ]),
    install_requires=[
        'psycopg2-binary',
        'sqlalchemy',
        'click',
        'python-dotenv',
        'sentence-transformers',
        'scikit-learn',
        'numpy',
        'pandas',
        'openai',
        'python-json-logger',
        'tabulate',
        'nltk',
        'spacy',
        'flask',
    ]
) 