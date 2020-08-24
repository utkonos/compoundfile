"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""
import pathlib
import setuptools

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / 'README.md').read_text(encoding='utf-8')

setuptools.setup(
    name='compoundfile',
    version='1.0.0',
    description='Python file parser for Microsoft compound files',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/pypa/compoundfile',
    author='Malware Utkonos',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Security',
    ],
    packages=setuptools.find_packages(),
    python_requires='>=3.8, <4',
    entry_points={
        'console_scripts': [
            'compoundfile=compoundfile.command_line:main',
        ],
    },
)
