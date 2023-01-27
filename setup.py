import setuptools

setuptools.setup(
   name='WSIMOD',
   version='0.2',
   author='Barnaby Dobson',
   author_email='b.dobson@imperial.ac.uk',
   packages=setuptools.find_packages(),
   license='LICENSE',
   description='WSIMOD is for simulating water quality and quantity',
   long_description=open('README.md').read(),
   install_requires=['tqdm','pytest','PyYAML'],
   extras_require={
        'demos': [ 
            'pandas', 
            'geopandas', 
            'matplotlib', 
            'shapely', 
            ],
      'documentation': 
      [
        'mkdocs',
        'mkdocs-autorefs',
        'mkdocs-bibtex',
        'mkdocs-coverage',
        'mkdocs-jupyter',
        'mkdocs-material',
        'mkdocs-material-extensions',
        'mkdocstrings',
        'mkdocstrings-python',
        'pypandoc',
        'demos'
      ]
    }
      )