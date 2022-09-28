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

### TEMPO_CONFIG_PATH

To be able to add secret configurations there is a default config path `/tempo` where secrets can be mounted as files.

For development purposes the environment variable *TEMPO_CONFIG_PATH* overrides the default value for config files.

### TEMPO_LOG_LEVEL

Tempo uses `logging` for logging, with the default log level `WARNING`. This can be changed by setting the environment variable *TEMPO_LOG_LEVEL* to any value in `["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]`

### Configuration files

#### Working hours JSON file

a simple json file with username and expected daily hours of work.
```json
[
    {"User" : "Bob Builder", "Daily" : 8 },
    ...
]
```
