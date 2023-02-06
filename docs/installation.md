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