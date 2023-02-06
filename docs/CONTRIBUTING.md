# Contributing to `WSIMOD`
Thank you for considering contributing to `WSIMOD`. 

## Bugs
Please create a new [issues](https://github.com/barneydobson/wsi/issues) if you may have found a bug. Please describe the bug and instructions on recreating it (including OS and Python version). It may be helpful to use examples from the [tutorials](https://barneydobson.github.io/wsi/tutorials/) or [how-to's](https://barneydobson.github.io/wsi/how-to/) to ensure that data is available.

## Confusion
If you are confused about how a model component works, or why it is producing results that look the way they do, please first check the [documentation](https://barneydobson.github.io/wsi) and existing [issues](https://github.com/barneydobson/wsi/issues). If this does not answer your question, or your question has not yet been raised, then please create a new issue where we can discuss it. 

## Creating new functionality
Is there something in the water cycle that you would like to represent that is not included in `WSIMOD`? Whatever it is, you are probably not alone! If there is not one already, please create an [issue](https://github.com/barneydobson/wsi/issues) where we can discuss it. Do this _before_ you start developing as others may be working on the same thing!

Although the development of new functionality will depend highly on the case, there are a few generalisable points to bear in mind:
 - `WSIMOD` is highly object-oriented, thus, we will always try to implement a new component as a subclass of the closest component. We will collaboratively discuss this in the issue.
 - Our [documentation](https://barneydobson.github.io/wsi) relies heavily on use of docstrings, make sure to format it following the [Google Python style](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html), see the source code of [`Land.__init__`](https://barneydobson.github.io/wsi/reference-land/#wsimod.nodes.land.Land.__init__) for an example. An admin will compile the documentation, but you can create your own pages to be added by following the directions [below](#create-documentation).
 - We are incredibly grateful for contributions that include new [tutorials](https://barneydobson.github.io/wsi/tutorials/) or [how-to's](https://barneydobson.github.io/wsi/how-to/), whether for new or existing functionality. Our use of the [mkdocs-jupyter](https://github.com/danielfrg/mkdocs-jupyter) extension enables notebooks to form pages in the documentation, but that can also serve as downloadable examples that people can run.
 - Design new tests that instantiate your new functionality and test that it produces a specified response. New tests are stored in the `wsi/tests/` folder. You can run tests by navigating to the folder and running:
    ```
    pytest # run all tests
    pytest tests/test_file.py # run a specific file's tests
    ```

    You can check the coverage for these tests by running:
    ```
    coverage run -m pytest
    coverage report
    ```

    And generate a new coverage html for the documentation with
    ```
    coverage html
    ```

## Create documentation

If you want to compile new documentation you will need to clone the reposistory and `pip install` WSIMOD with some additional packages:

```
pip install .[documentation]
```

Navigate to `docs` and run the following to create the component library:
```
python create_class_page.py
```


And then open python, and run:
```
import pypandoc
pypandoc.download_pandoc()
```

From here, you can make changes to the documentation pages in `docs` and view how they appear by navigating to and hosting them locally:

```
mkdocs serve
```

If compiling documentation, you will need to install `git`:
```
conda install git
```

And deploy:
```
mkdocs gh-deploy
```