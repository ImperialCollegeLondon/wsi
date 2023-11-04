# Installation

Create and activate new conda environment

```bash
conda create --name wsimod python=3.10
conda activate wsimod
```

Install a GUI if you like

```bash
conda install spyder -c conda-forge
```

Install WSIMOD directly from GitHub

```bash
pip install https://github.com/barneydobson/wsi/archive/refs/heads/main.zip
```

Use `[demos]` to include the demos and tutorials.

```bash
pip install https://github.com/barneydobson/wsi/archive/refs/heads/main.zip
pip install wsimod[demos]
```

If you want to make changes WSIMOD you can download/clone this folder, navigate to it, and run:

```bash
python setup.py develop
```

or (with demos)

```bash
python setup.py develop easy_install "wsimod[demos]"
```
