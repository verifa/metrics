# Verifa Metrics Dashboard

## Requirements

* Docker daemon or Podman (see below under Replacing Docker)
* Python 3 <span style="color:red">**NOTE (2023.10.12): the project fails with Python 3.12 due to an issue with numpy**</span>
* [python-poetry](https://python-poetry.org/) to manage dependencies. (Install: <https://python-poetry.org/docs/#osx--linux--bashonwindows-install-instructions>)

Check the [pyproject.toml](./pyproject.toml) for Python requirements. These are handled by Poetry.

## Development

```TEMPO_KEY``` is required. See [Runtime environment](#runtime-environment) below.

```bash
# Build the image
make dev
```
```bash
# Run a container with the built image
make run
# Browse http://localhost:8000
```
```bash
# For more details about the different make targets
make help
```

### TEMPO_CONFIG_PATH
the run target uses the environment variable TEMPO_CONFIG_PATH, described below, as a mount point if set

```Makefile
ifneq ($(TEMPO_CONFIG_PATH),)
  vmounts=-v $(TEMPO_CONFIG_PATH):/tempo
else
  vmounts=
endif
```

To run a container that ignores the optional environment variable

```bash
make bare
# Browse http://localhost:8000
```

### Replacing Docker
To use `podman`, you can set the `DOCKER` variable to `podman`, e.g. `make DOCKER=podman run`

### Running on Windows
To run on GitBash for Windows, you can set the `DOCKER` variable to `winpty docker`, e.g. `make DOCKER='winpty docker' run`.

Docker for Windows satisfies the Docker requirement.

## Runtime environment

| Key | Notes |
|-----|-------|
| **TEMPO_KEY** <br/> (required) | Tempo API key. Can be generated from **Tempo → Settings (left sidebar) → API Integration**. |
| **TEMPO_CONFIG_PATH** <br/> (optional) | To be able to add secret configurations there is a default config path `/tempo` where secrets can be mounted as files. For development purposes the environment variable *TEMPO_CONFIG_PATH* overrides the default value for config files. |
| **TEMPO_LOG_LEVEL** <br/> (optional) | Tempo uses `logging` for logging, with the default log level `WARNING`. This can be changed by setting the environment variable *TEMPO_LOG_LEVEL* to any value in `["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` |
| **NOTION_KEY** <br/> (optional) | Notion API key. Obtained from https://www.notion.so/my-integrations. You must be an owner of the workspace containing the databases. |
| **NOTION_OKR_DATABASE_ID** <br/> (optional) | *Requires: NOTION_KEY* <br/> The ID for a specific database in Notion, see [this](https://stackoverflow.com/questions/67728038/where-to-find-database-id-for-my-database-in-notion) link. |
| **NOTION_OKR_LABELS** <br/> (optional) | *Requires: NOTION_KEY and NOTION_OKR_DATABASE_ID* <br/> The labels used in Notion. |
| **NOTION_FINANCIAL_DATABASE_ID** <br/> (optional) | *Requires: NOTION_KEY* <br/> Like the example of *NOTION_OKR_DATABASE*, a database ID from notion is needed. The database should include the column names `Month`, `external-cost`, and `real-income`. |
| **NOTION_WORKINGHOURS_DATABASE_ID** <br/> (optional) | *Requires: NOTION_KEY* <br/> Like the example of *NOTION_OKR_DATABASE*, a database ID from notion is needed. The database should include the column names `User`, `Daily`, `Delta`, `Start`, and `Stop`. |
| **NOTION_ALLOCATIONS_DATABASE_ID** <br/> (optional) | *Requires: NOTION_KEY* <br/> Like the example of *NOTION_OKR_DATABASE*, a database ID from notion is needed. The database should include the column names `Allocation`, `Assign`, `Task ID`, `Unconfirmed`, and `Date` (as a date range). |

## Configuration files

Metrics is expecting a simple layout for the optional configuration files. A folder structure found in `/tempo` or, if set, in ${TEMPO_CONFIG_PATH}.

```bash
.
└── rates
    └── data.json
```

### Rates

The rates file contains 4 lists
- *Default* is a list with project issue keys, rate and currency
- *Exceptions* is a list of with exceptions if different users have a different rate for the same issue key
- *Internal* is a list of tempo project is considered internal, even if they are set to billable in tempo
- *Currency* is a list of exchange rates, € is the currency used in the metrics, so for other currencies a simple conversion is used

```json
{
  "Default": [
    {
      "Key": "CUS-1",
      "Rate": "100",
      "Currency": "EUR"
    },
    {
      "Key": "AB-1",
      "Rate": "1000",
      "Currency": "SEK"
    },
  ],
  "Exceptions": [
    {
      "Key": "CUS-1",
      "Rate": "125",
      "User": "Alice Architect"
    }
  ],
  "Internal": [
    {
      "Key": "US"
    }
  ],
  "Currency": [
    {
      "SEK2EUR": "0.1"
    }
  ]
}
```


## Locally building the documentation
```bash
    make docs
```
Then open `docs/_build/html/index.html`
