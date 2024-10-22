# Welcome to WSIMOD <img style="float: right;" src="./docs/images/wsimod_logo_png.png" alt="WSIMOD logo">

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

You can access our documentation below or at [https://imperialcollegelondon.github.io/wsi](https://imperialcollegelondon.github.io/wsi).

*Requires*: Python 3 (tested on versions >=3.7), [tqdm](https://tqdm.github.io/), [PyYAML](https://pyyaml.org/), [dill](https://dill.readthedocs.io/en/latest/)

*Optional requirements to run demos*: [Pandas](https://pandas.pydata.org/), [GeoPandas](https://geopandas.org/en/stable/), [Matplotlib](https://matplotlib.org/), [Shapely](https://shapely.readthedocs.io/en/stable/manual.html)

Please consider [contributing](./docs/CONTRIBUTING.md) and note the [code of conduct](./docs/CODE_OF_CONDUCT.md)

If you use WSIMOD, please make sure to [cite](#how-to-cite-wsimod).

## Table Of Contents

The documentation follows the best practice for
project documentation as described by Daniele Procida
in the [Diátaxis documentation framework](https://diataxis.fr/)
and consists of:

1. [About](https://imperialcollegelondon.github.io/wsi/paper/paper/)

2. [Installation](https://imperialcollegelondon.github.io/wsi/installation/)

3. [Tutorials](https://imperialcollegelondon.github.io/wsi/tutorials/)

4. [How-To Guides](https://imperialcollegelondon.github.io/wsi/how-to/)

5. [Component library](https://imperialcollegelondon.github.io/wsi/component-library/)

6. [API reference](https://imperialcollegelondon.github.io/wsi/reference/)

7. [Quickstart](https://imperialcollegelondon.github.io/wsi/demo/scripts/quickstart_demo/)

8. [Coverage](https://imperialcollegelondon.github.io/wsi/coverage/)

## Installation

Install WSIMOD directly from GitHub

```bash
pip install https://github.com/ImperialCollegeLondon/wsi/archive/refs/heads/main.zip
```

Use `[demos]` to include the demos and tutorials.

```bash
pip install https://github.com/ImperialCollegeLondon/wsi/archive/refs/heads/main.zip
pip install wsimod[demos]
```

If you want to make changes to WSIMOD you can download/clone this folder, navigate to it, and run:

```bash
pip install -e .[dev]
```

or (with demos)

```bash
pip install -e .[dev,demos]
```

## How to cite WSIMOD

[![DOI](https://joss.theoj.org/papers/10.21105/joss.04996/status.svg)](https://doi.org/10.21105/joss.04996)
[![DOI](https://img.shields.io/badge/GMD-10.5194/gmd--17--449--2024-brightgreen)](https://doi.org/10.5194/gmd-17-4495-2024)

If you would like to use our software, please cite it using the following:

 > Dobson, B., Liu, L. and Mijic, A. (2023)
 ‘Water Systems Integrated Modelling framework, WSIMOD: A Python package for integrated modelling of water quality and quantity across the water cycle’,
 Journal of Open Source Software.
 The Open Journal,
 8(83),
 p. 4996.
 doi: 10.21105/joss.04996.

Find the bibtex citation below:

```bibtex
@article{Dobson2023,
        doi = {10.21105/joss.04996},
        url = {https://doi.org/10.21105/joss.04996},
        year = {2023},
        publisher = {The Open Journal},
        volume = {8},
        number = {83},
        pages = {4996},
        author = {Barnaby Dobson and Leyang Liu and Ana Mijic},
        title = {Water Systems Integrated Modelling framework, WSIMOD: A Python package for integrated modelling of water quality and quantity across the water cycle},
        journal = {Journal of Open Source Software}
        }
```

Please also include citation to the WSIMOD theory paper:

 > Dobson, B., Liu, L. and Mijic, A. (2024)
 ‘Modelling water quantity and quality for integrated water cycle management with the Water Systems Integrated Modelling framework (WSIMOD) software’,
 Geoscientific Model Development.
 Copernicus Publications,
 17(10),
 p. 4495.
 doi: 10.5194/gmd-17-4495-2024

Find the bibtex citation below:

```bibtex
@article{gmd-17-4495-2024,
        author = {Barnaby Dobson and Leyang Liu and Ana Mijic},
        title = {Modelling water quantity and quality for integrated water cycle management with the Water Systems Integrated Modelling framework (WSIMOD) software},
        journal = {Geoscientific Model Development},
        volume = {17},
        year = {2024},
        number = {10},
        pages = {4495--4513},
        url = {https://gmd.copernicus.org/articles/17/4495/2024/},
        doi = {10.5194/gmd-17-4495-2024}
}
```

## Acknowledgements

WSIMOD was developed by [Barnaby Dobson](https://github.com/barneydobson) and [Leyang Liu](https://github.com/liuly12).
Theoretical support was provided by Ana Mijic.
Testing the WSIMOD over a variety of applications has been performed by
Fangjun Peng, Vladimir Krivstov and Samer Muhandes.
Software development support was provided by Imperial College's Research
Software Engineering service, in particular from Diego Alonso and Dan Davies.

We are incredibly grateful for the detailed software reviews provided by [Taher Chegini](https://github.com/cheginit) and [Joshua Larsen](https://github.com/jlarsen-usgs) and editing by [Chris Vernon](https://github.com/crvernon). Their suggestions have significantly improved WSIMOD.

The design of WSIMOD was significantly influenced by
[CityDrain3](https://github.com/gregorburger/CityDrain3),
[OpenMI](https://www.ogc.org/standards/openmi),
[Belete, Voinov and Laniak, (2017)](https://doi.org/10.1016/j.envsoft.2016.10.013),
and [smif](https://github.com/tomalrussell/smif).

We acknowledge funding from the CAMELLIA project (Community Water Management
for a Liveable London), funded by the Natural Environment Research Council
(NERC) under grant NE/S003495/1.
