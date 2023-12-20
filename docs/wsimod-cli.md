# WSIMOD Command Line Interface

WSIMOD can be run from the command line using an input config file (and any other data
file required). This is convenient as it removes the need of any knowledge of Python,
for example.

## Syntax

The syntax for running WSIMOD from the command line is as follows:

```output
usage: WSIMOD [-h] [--inputs INPUTS] [--outputs OUTPUTS] settings

positional arguments:
  settings              Path to the WSIMOD input file, in YAML format.

options:
  -h, --help            show this help message and exit
  --inputs INPUTS, -i INPUTS
                        Base directory for all input files. If present, overwrites value in the settings file.
  --outputs OUTPUTS, -o OUTPUTS
                        Base directory for all output files. If present, overwrites value in the settings file.
```

Only the `settings` argument is mandatory. All the others can be obtained from this one.

## Types of input files

WSIMOD command line interface (CLI) supports two types of input settings files:

### Saved model file

Created with `Model.save`, as described in the
[WSIMOD models section](wsimod_models.md), in `yaml` format. As `save` creates extra
data files to store the required tabular data, those files also need to be present and
in the right location (typically, alongside the config file). As this file has been
created out of a fully constructed model, it tends to be verbose including all the
default values for the different arguments used by WSIMOD.

### Custom model file

This is a manually created `yaml` file with the definition of
the model. It is identical to the previous file except that:

- Is less verbose, as it only includes the options that need customisation and not
all the defaults.
- Can include an `inputs` and an `outputs` keys to indicate the location of the
inputs and outputs, identical in purpose to the CLI arguments.
- Can include a `data` key where instructions for the pre-processing of the input
files can be included.

The last option is the most fundamental difference and it gives the second approach
greater flexibility. In this case, the relevant input that should be a dataset is
replaced with `data:some_instructions`, and an entry in the `data` section of the file
is included to explain what those instructions are.

For example, the [quickstart demo](./../demo/scripts/quickstart_demo) has two parameters
that are datasets, the `dates` and the `land_inputs` of the `land` node. Both of these
come from the same input file, `timeseries_data.csv`.

For the `dates`, the way to indicate them in the settings file would be:

```yaml
data:
  dates_data:
    filename: timeseries_data.csv
    options: usecols=['date'],parse_dates=['date']

dates: data:dates_data
```

We are indicating that the `dates` should be taken from a specific column of the CSV
file and that the column should be parsed as dates. The arguments included in `options`
are passed to the underlaying [`pandas.read_csv` function](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html),
and therefore it is possible to have a high degree of customisation when loading files.
The main caveat is that only simple python types are allowed in the options
(strings, lists, etc.) so the more complex processing options that are possible in
`read_csv` might not be available.

The `land_inputs` requires more manipulation:

```yaml
data:
  my_land_data:
    filename: timeseries_data.csv
    filter:
      - where: site
        is: oxford_land
    scaling:
      - where: variable
        is: precipitation
        variable: value
        factor: "MM_TO_M"
    format: dict
    index: ['variable', 'date']
    output: 'value'
    options: parse_dates=['date']

- type_: Land
  data_input_dict: data:my_land_data
  ... # Other arguments
```

In this case, we are using the same input file, but we are processing it in a different
way. We are still parsing the `date` column as dates, but then, *after reading the CSV*
we are doing the following maniputlations in exactly this order:

- We are selecting only entries where the `site` is `oxford_land`. Several filters can
be applied sequentially, applied to different columns.
- We are scaling the values of the variable `precipitation` to match the correct units.
A number or a [units conversion factor](reference-core.md) can be used, and multiple
scalings can be applied sequentially to different columns.
- The index is set to the chosen variables, so the records can be selected based on
that. In this case, records will be selected based on a couple of (`variable`, `date`).
- The relevant column will be selected as `output`. In this case, the column is `value`.
- Finally, the format of the data that will be ingested by the WSIMOD model is chosen.
In this case, we choose a `dict` format, which is what WSIMOD requires in nodes and
arcs. Note that we did not do this conversion for the dates above.

As it can be seen, while this manipulation is somewhat limited in the grand scheme of
things, it already offers a lot of flexibility. For example, if we want to repeat the
very same analysis but with `thames` instead of `oxford_land`, we just need to replace
that argument in the input and everythig else is kept the same.

## Output files

As a result of a WSIMOD simulation, there will always be 3 CSV files created:

- `flows.csv`
- `surfaces.csv`
- `tanks.csv`

See the output of [`Model.run` in the documentaiton](reference-model.md) for a
description of the contents of these files.
