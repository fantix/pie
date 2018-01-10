import setuptools

setuptools.setup(
    name="pie",
    version="1.0",
    url="https://decentfox.com/pie",

    author="DecentFoX Studio",
    author_email="service@decentfox.com",

    description="Platform for Internet Enterprise.",
    long_description=open('README.rst').read(),

    packages=setuptools.find_packages(),

    install_requires=[
        'aioredis==1.0.0',
        'alembic==0.9.6',
        'gino',
        'psycopg2==2.7.3.2',
        'sanic==0.7.0',
    ],

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
