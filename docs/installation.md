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
python setup.py develop
```

or (with demos)

```
python setup.py develop easy_install "wsimod[demos]"
```

If you want to compile new documentation you will need to install some additional packages

```
python setup.py develop easy_install "wsimod[documentation]"
```

And then open python, and run:
```
import pypandoc
pypandoc.download_pandoc()
```