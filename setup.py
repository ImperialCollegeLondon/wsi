import setuptools


with open("requirements.txt") as f:
    install_requires = f.read().splitlines()

with open("requirements_demos.txt") as f:
    demos_requires = f.read().splitlines()

with open("requirements_documentation.txt") as f:
    docs_requires = f.read().splitlines() + demos_requires

setuptools.setup(
   name='WSIMOD',
   version='0.2',
   author='Barnaby Dobson',
   author_email='b.dobson@imperial.ac.uk',
   packages=setuptools.find_packages(),
   license='LICENSE',
   description='WSIMOD is for simulating water quality and quantity',
   long_description=open('README.md').read(),
   install_requires=install_requires,
   extras_require={
        'demos': demos_requires,
      'documentation': docs_requires
    }
      )