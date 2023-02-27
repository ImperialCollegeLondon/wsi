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
    orcid: 0000-0001-7556-1134
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

Traditional approaches to water system modelling broadly fall into highly 
numerical models that excel in representing individual subsystems, or systems 
dynamics models that create broad representations but that lack a physical 
basis. Early attempts at a physical representation of the water cycle combined 
existing numerical models through an integration framework [@Rauch:2017]. While 
successful, this approach has an incredibly high user burden because each 
subsystem model is so detailed, and as a consequence is also difficult to 
customise. To illustrate, SWAT is one of the most widespread models of the 
rural water cycle [@Arnold:2012], while SWMM is the same but for the urban 
water cycle [@Gironas:2010]. It has been demonstrated that these two software 
can interface using the OpenMI integration framework [@Shrestha:2013]. Despite 
this seemingly powerful combination of two near-ubiquitous models, integrated 
applications have been limited, and we propose that this is for the same 
reasons presented in [@Rauch:2017]: user burden and customisation difficulty. 

Because of this need, we provide a parsimonious and self-contained suite for integrated water cycle modelling in the WSIMOD Python package. It 
brings together a range of software developed over the course of three years 
on the [CAMELLIA project](https://www.camelliawater.org/). Urban water 
processes are based on those presented and validated in the CityWat 
model [@Dobson:2020;@Dobson:2021;@Dobson:2022;@Muhandes:2022], while
hydrological and agricultural processes are from the CatchWat 
model [@Liu:2022;@Liu:2022b]. WSIMOD also provides an interface for message
passing between different model components, enabling all parts of the water 
cycle to interact with all other parts. The result is a simulation model that
is easy to set up, highly flexible and ideal for representing water quality and
quantity in 'non-textbook' water systems (which in our experience is nearly 
all of them). 

The package provides a variety of tutorials and examples to help modellers 
create nodes (i.e., representations of subsystems within the water cycle), 
connect them together with arcs (i.e., representing the fluxes between 
subsystems), and orchestrate them into a model that creates simulations. 

## Limitations
We highlight that WSIMOD is not intended to be a substitute for sophisticated 
physical models, nor for a system dynamics approach. In applications where 
detailed hydraulic/hydrological process representations are needed (e.g., 
informing the design of specific pipes, cases where processes are hard to
quantify such as representing social drivers of population growth, etc.) there 
are likely better tools available. Our case studies highlight 
that WSIMOD is most useful in situations where physically representing 
cross-sytem processes and thus capturing the impacts of cross-system 
interactions are essential towards the questions you ask of your model. 
Secondary benefits are that the parsimonious representations utilised are 
computationally fast and flexible in capturing a wide range of system 
interventions.

# Acknowledgements

WSIMOD was developed by [Barnaby Dobson](https://github.com/barneydobson) and [Leyang Liu](https://github.com/liuly12). 
Theoretical support was provided by Ana Mijic.
Testing the WSIMOD over a variety of applications has been performed by 
Fangjun Peng, Vladimir Krivstov and Samer Muhandes.
Software development support was provided by Imperial College's Research 
Software Engineering service, in particular from Diego Alonso and Dan Davies.

We are incredibly grateful for the detailed software reviews provided by [Taher Chegini](https://github.com/cheginit) and [Joshua Larsen](https://github.com/jlarsen-usgs) and editing by [Chris Vernon](https://github.com/crvernon). Their suggestions have significantly improved WSIMOD.

The design of WSIMOD was significantly influenced by 
[CityDrain3](https://github.com/gregorburger/CityDrain3) [@Burger:2016], 
[OpenMI](https://www.ogc.org/standards/openmi) [@Gregersen:2007], [smif](https://github.com/tomalrussell/smif) [@smif_paper;@smif_software], and the 
following review [@Belete:2017].

We acknowledge funding from the CAMELLIA project (Community Water Management 
for a Liveable London), funded by the Natural Environment Research Council 
(NERC) under grant NE/S003495/1.

# References
