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

## Runtime environment

### TEMPO_KEY

To read data from tempo, the API key to use is expected as the TEMPO_KEY environment variable.

### TEMPO_CONFIG_PATH

To be able to add secret configurations there is a default config path `/tempo` where secrets can be mounted as files.

For development purposes the environment variable *TEMPO_CONFIG_PATH* overrides the default value for config files.

### Configuration files

#### workinghours.json

a simple json file with username and expected daily hours of work.
```json
[
    {"User" : "Bob Builder", "Daily" : 8 },
    ...
]
```
