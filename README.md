# Welcome to WSIMOD

WSIMOD stands for the Water Systems Integrated Modelling framework.

The terrestrial water cycle is a highly interconnected system where the 
movement of water is affected by physical and human processes. Thus, 
environmental models may become inaccurate if they do not provide a complete 
picture of the water cycle, missing out on unexpected opportunities and 
omitting impacts that arise from complex interactions. WSIMOD is a modelling 
framework to integrate these different processes. It provides a message passing 
interface to enable different subsystem models to communicate water flux and 
water quality information between each other, and self-contained 
representations of the key parts of the water cycle (rivers, reservoirs, urban 
and rural hydrological catchments, treatment plants, and pipe networks).
We created WSIMOD to enable a user greater flexibility in setting up their 
water cycle models, motivated by the abundance of non-textbook water systems 
that we have experienced in industry collaboration. The WSIMOD Python package 
provides tutorials and examples to help modellers create nodes, connect them 
with arcs, and create simulations.

You can access our documentation below or at [https://barneydobson.github.io/wsi](https://barneydobson.github.io/wsi).

*Requires*: Python 3 (tested on versions >=3.7), [tqdm](https://tqdm.github.io/), [PyYAML](https://pyyaml.org/)

*Optional requirements to run demos*: [Pandas](https://pandas.pydata.org/), [GeoPandas](https://geopandas.org/en/stable/), [Matplotlib](https://matplotlib.org/), [Shapely](https://shapely.readthedocs.io/en/stable/manual.html)

## Table Of Contents

The documentation follows the best practice for
project documentation as described by Daniele Procida
in the [Diátaxis documentation framework](https://diataxis.fr/)
and consists of:

1. [About](https://barneydobson.github.io/wsi/paper/paper/)

2. [Installation](https://barneydobson.github.io/wsi/installation/)

3. [Tutorials](https://barneydobson.github.io/wsi/tutorials/)

4. [How-To Guides](https://barneydobson.github.io/wsi/how-to/)

5. [Component library](https://barneydobson.github.io/wsi/component-library/)

6. [API reference](https://barneydobson.github.io/wsi/reference/)

7. [Quickstart](https://barneydobson.github.io/wsi/demo/scripts/quickstart_demo/)

8. [Coverage](https://barneydobson.github.io/wsi/coverage/)

## Installation
Create and activate new conda environment
```
conda create --name wsimod python=3.10
conda activate wsimod
```

Install a GUI if you like
```
conda install spyder -c conda-forge
```

Install WSIMOD directly from GitHub
```
pip install https://github.com/barneydobson/wsi/archive/refs/heads/main.zip
```

Use `[demos]` to include the demos and tutorials.
```
pip install -e https://github.com/barneydobson/wsi/archive/refs/heads/main.zip[demos]
```

If you want to make changes WSIMOD you can download/clone this folder, navigate to it, and run:
```
pip install .
```

or (with demos)

```
pip install -e .[demos]
```

## Acknowledgements

WSIMOD was developed by Barnaby Dobson and Leyang Liu. 
Theoretical support was provided by Ana Mijic.
Testing the WSIMOD over a variety of applications has been performed by 
Fangjun Peng, Vladimir Krivstov and Samer Muhandes.
Software development support was provided by Imperial College's Research 
Software Engineering service, in particular from Diego Alonso and Dan Davies.

The design of WSIMOD was significantly influenced by 
[CityDrain3](https://github.com/gregorburger/CityDrain3), 
[OpenMI](https://www.ogc.org/standards/openmi), 
[Belete, Voinov and Laniak, (2017)](https://doi.org/10.1016/j.envsoft.2016.10.013), 
and [smif](https://github.com/tomalrussell/smif).

We acknowledge funding from the CAMELLIA project (Community Water Management 
for a Liveable London), funded by the Natural Environment Research Council 
(NERC) under grant NE/S003495/1.
