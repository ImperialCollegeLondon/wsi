# Run WSIMOD in DAFNI

WSIMOD is available to run in DAFNI, the Data & Analytics Facility for National
Infrastructure to advance UK infrastructure research. This let you run WSIMOD
simulations, and combining them with other tools, without the need of installing any
of them.

Assuming you have a DAFNI account, the steps to run a WSIMOD simulation will be the
following:

- In the `Data` tab:
  - Upload the input `YAML` file as a dataset. Please note that if your `YAML` file
  contains `extensions` section, it should include additional linux path strings as
  follows:
  `extensions: [
    /data/inputs/extension_1.py,
    /data/inputs/extension_2.py,
    ]`
  - Upload any other required input files as another dataset. This can contain
    multiple files.
- In the `Workflow` tab select the `WSIMOD workflow`.
- In the `Parameter sets` section, click `Create`.
- In the page that opens, select the model in the workflow (typically `model-1`), and
complete the sections at the bottom with the appropriate information:
  - In the `Parameters`, choose the name of the settings file (normally
    `settings.yaml` or `config.yaml`)
  - In the `Datasets`, click in the pen icon and select the datasets you just uploaded
    for the input `YAML` and the other data files. These all will be put together in the
    same directory when running the simulation.
- Unselect `model-1`, click `Continue` and complete the required metadata in the next
screen, like the name of the parameter set.
- Finally, click in `Execute workflow with parameter set`.

If all goes well, you should then see in the `Workflow` page, `Instances` section, that
there is a new `Instance` of WSIMOD running. After some time (dending on the
complexity of the model and the load of the system), the run will finish and there
will be a new `WISMOD output` dataset available in the `Data` tab.

You can create new workflows to customise this process, name of the outputs, and even
chain multiple models, one after the other.
