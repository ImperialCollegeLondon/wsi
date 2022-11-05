---
title: 'Water Systems Integrated Modelling framework, WSIMOD: A Python package for integrated modelling of water quality and quantity across the water cycle'
tags:
  - Python
  - water quality
  - hydrology
  - integrated modelling
  - pollution
authors:
  - name: Barnaby Dobson
    orcid: 0000-0002-0149-4124
    affiliation: 1
  - name: Leyang Liu
    affiliation: 1
  - name: Ana Mijic
    orcid: 0000-0001-7096-9405
    affiliation: 1
affiliations:
 - name: Department of Civil and Environmental Engineering, Imperial College London, UK
   index: 1
date: 04 November 2022
bibliography: paper.bib

---

# Summary

The water cycle is highly interconnected; water fluxes in one part depend on 
physical and human processes throughout. For example, rivers are a water 
supply, a receiver of wastewater, and an aggregate of many hydrological, 
biological, and chemical processes. Thus, simulations of the water cycle that
have highly constrained boundaries may miss key interactions that create 
unanticipated impacts or unexpected opportunities [@Dobson:2020;@Liu:2022]. 
Integrated environmental models aim to resolve the issue of boundary 
conditions, however they have some key limitations [@Rauch:2017], and in 
particular we find a significant need for a parsimonious, self-contained suite 
that is accessible and easy to setup. 

# Statement of need

WSIMOD is a Python package for integrated modelling of the water cycle. It 
brings together a range of software developed over the course of three years 
on the [CAMELLIA project](https://www.camelliawater.org/). Urban water 
processes are based on those presented and validated in the CityWat model 
[@Dobson:2020;@Dobson:2021;@Dobson:2022;@Muhandes:2022], while hydrological 
and agricultural processes are from the CatchWat model [@Liu:2022;@Liu:2022b]. 
WSIMOD also provides an interface for message passing between different 
model components, enabling all parts of the water cycle to interact with all 
other parts. The result is a simulation model that is easy to set up, highly 
flexible and ideal for representing water quality and quantity in 'non-
textbook' water systems (which in our experience is nearly all of them). 

The package provides a variety of tutorials and examples to help modellers 
create nodes (i.e., representations of subsystems within the water cycle), 
connect them together with arcs (i.e., representing the fluxes between 
subsystems), and orchestrate them into a model that creates simulations. 

# Acknowledgements

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

# References
\bibliography