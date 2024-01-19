# Installation

It is highly recommended to setup a virtual environment to install WSIMOD into. This
way, its installation and that of its dependencies will not interfere with any other
tool in your system.

Here we use a `conda` environment which let us use the version of python we want to use,
but you can use any other tool you are familiar with.

```bash
conda create --name wsimod python=3.10
conda activate wsimod
```

You can install the stable version of WSIMOD from [PyPI.org](https://pypi.org/) with:

```bash
pip install wsimod
```

If you want to install the development version, you can innstall WSIMOD directly from
GitHub with:

```bash
pip install git+https://github.com/ImperialCollegeLondon/wsi@main
```

Use `[demos]` to include the dependencies required to run the demos and tutorials.

```bash
pip install wsimod[demos]
```

## Developing WSIMOD

If you want to help developing WSIMOD, or just modify it locally for your own interests,
please read throgh the [CONTRIBUTING guidelines](https://github.com/ImperialCollegeLondon/wsi/blob/main/docs/CONTRIBUTING.md)
in the GitHub repository.
