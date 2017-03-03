from setuptools import setup, find_packages

setup(
        name='syncthingmanager',
        version='0.1.0-dev1',
        description='A commandline tool for controlling the Syncthing API',
        url ='https://github.com/classicsc/syncthingmanager',
        author='Samuel Smoker',
        author_email='smoker@usc.edu',
        license='GPLv3',
        classifiers = [
            'Development Status :: 3 - Alpha',
            'Intended Audience :: End Users/Desktop',
            'Intended Audience :: System Administrators',
            'Intended Audience :: Developers',
            'Topic :: System :: Archiving :: Mirroring',
            'Topic :: Utilities',
            'Natural Language :: English',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
            'Programming Language :: Python :: 3.4',
        ],
        keywords = 'syncthing',
        packages = ['syncthingmanager'],
        install_requires = ['syncthing'],
        extras_require={
            'test': ['pytest']
        },
        entry_points={
            'console_scripts': [
                'stman=syncthingmanager:main',
            ],
        },
)
