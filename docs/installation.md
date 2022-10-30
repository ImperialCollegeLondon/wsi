Create and activate new conda environment
```
conda create --name wsimod python=3.10
conda activate wsimod
```

Install a GUI if you like
```
conda install spyder -c conda-forge --verbose
```

Install geopandas separately (because it is naughty)
```
conda install geopandas -c conda-forge --verbose
```

Download or clone this folder, navigate to it, and run:
```
python setup.py develop
```