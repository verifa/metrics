# Verifa Metrics Dashboard

TODO: basically everything...

## Development

This project uses [python-poetry](https://python-poetry.org/) to manage dependencies.

Installing poetry: <https://python-poetry.org/docs/#osx--linux--bashonwindows-install-instructions>

Check the [pyproject.toml](./pyproject.toml) for Python requirements.

Then simply:

```bash
# Run the dev server
make dev
# Browse to http://localhost:8050
```

or to run a container with the built image

```bash
make run
# Browse http://localhost:8000
```

*Note:* To use `podman`, you can set the `DOCKER` variable to `podman`, e.g. `make DOCKER=podman dev`

For more details about the different make target

```bash
make help
```

## Runtime environment

### TEMPO_KEY

To read data from tempo, the API key to use is expected as the TEMPO_KEY environment variable.

### Metrics configuration

The metrics application gives 2 options how to enable the configuration files, described below, to be available run-time. There is a default config path `/tempo-config` where the secret files are expected to be found.

#### Config files in git

There are 3 environment variables that enables to keep the config files in a private git repository, that will be cloned to the default path when the application starts up.

- *TEMPO_CONFIG_REPO* the name of the repository, e.g. github.com/verifa/secrets
- *TEMPO_CONFIG_USER* a user that has http access to the repo
- *TEMPO_CONFIG_PASSW* the password for repo access

#### TEMPO_CONFIG_PATH

For development purposes the environment variable *TEMPO_CONFIG_PATH* overrides the default value for config files.

### Files

#### workinghours.json

a simple json file with username and expected daily hours of work, if to show this user in the "delta hours" table and from what date the delta hours is calculated for this user
```json
[
    {"User" : "Bob Builder",
        "Daily" : 8,
        "Show" : true,
        "Delta_start" : "*"}
    ...
]
```

#### rates.json

a simple json file that contains what rates to use for each task in tempo, listd of exceptions, internal projects, and simple currency converter numbers.

```json
{
  "Default": [
    {"Key" : "EX-1", "Rate" : "90", "Currency" : "EUR"},
    {"Key" : "EX-2", "Rate" : "90", "Currency" : "EUR"},
    ...
  ],
  "Exceptions": [
    {"Key" : "EX-1", "Rate" : "125", "User" : "Bob Builder" },
    ...
  ],
  "Internal": [
    {"Key" : "US" },
    ...
  ],
  "Currency": [
    {"SEK2EUR" : "0.1" },
    ...
  ]
}
```

#### costs.json

A file that list the monthly costs i EUR.

```json
[
  {"Month" : "2021-01", "Cost" : "12345"},
  ...
]
```
