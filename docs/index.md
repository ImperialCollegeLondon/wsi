# Welcome to WSIMOD

This is the documentation for the [WSIMOD project](https://github.com/barneydobson/wsi).
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

## Table Of Contents

The documentation follows the best practice for
project documentation as described by Daniele Procida
in the [Diátaxis documentation framework](https://diataxis.fr/)
and consists of:

1. [About](./paper/paper.md)

2. [Installation](installation.md)

3. [Tutorials](tutorials.md)
    
    3.1. [Quickstart](./demo/scripts/quickstart_demo.py)
    
    3.2. [WSIMOD model demonstration - Oxford](./demo/scripts/oxford_demo.py)
    
    3.3. [Land nodes - hydrology and agriculture](./demo/scripts/land_demo.py)

4. [How-To Guides](how-to.md)

    4.1. [Customise a node](./demo/scripts/customise_a_node.py)

    4.2. [Customise an arc](./demo/scripts/customise_an_arc.py)

5. [API reference](reference.md)
    
    5.1. [API reference - arc](reference-arc.md)
    
    5.2. [API reference - core](reference-core.md)
    
    5.3. [API reference - land](reference-land.md)
    
    5.4. [API reference - nodes](reference-nodes.md)
    
    5.5. [API reference - sewer](reference-sewer.md)
    
    5.6. [API reference - storage (reservoir, river, groundwater)](reference-storage.md)
    
    5.7. [API reference - wtw](reference-wtw.md)
    
    5.8. [API reference - other components](reference-other.md)

    5.9. [API reference - model](reference-model.md)

6. [Coverage](coverage.md)

## Acknowledgements

WSIMOD was developed by Barnaby Dobson and Liu Leyang. 
Theoretical support was provided by Ana Mijic.
Testing the WSIMOD over a variety of applications has been performed by 
Fangjun Peng, Vladimir Krivstov and Samer Muhandes.

The design of WSIMOD was significantly influenced by 
[CityDrain3](https://github.com/gregorburger/CityDrain3), 
[OpenMI](https://www.ogc.org/standards/openmi), 
[Belete, Voinov and Laniak, (2017)](https://doi.org/10.1016/j.envsoft.2016.10.013), 
and [smif](https://github.com/tomalrussell/smif).

We acknowledge funding from the CAMELLIA project (Community Water Management 
for a Liveable London), funded by the Natural Environment Research Council 
(NERC) under grant NE/S003495/1.