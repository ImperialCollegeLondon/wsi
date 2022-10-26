# wsimod
## Installation

Create and activate new conda environment
```
conda create --name wsimod python=3.10
conda activate wsimod
```

Install geopandas separately (because it is naughty)
```
conda install geopandas -c conda-forge --verbose
```

Download or clone this folder, navigate to it, and run:
```
python setup.py develop
```

## Structure of this repository

```
|---- projects
|    |---- partition
|    |    |---- scripts
|    |    |---- data
|    |    |    |---- cranbrook
|    |    |    |    |---- raw
|    |    |    |    |---- processed
|    |    |    |    |---- results
|    |---- ...
|---- wsimod
|    |---- core
|    |---- orchestration
|    |---- nodes
|    |---- arcs
|    |---- preprocessing
```
