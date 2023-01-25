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
   install_requires=['tqdm','pytest'],
   extras_require={
        'demos': [ 
            'pandas', 
            'geopandas', 
            'matplotlib', 
            'shapely', 
            ],
    }
      )
