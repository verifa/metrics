# Verifa Metrics Dashboard

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

*Note:* To use `podman`, you can set the `DOCKER` variable to `podman`, e.g. `make DOCKER=podman dev`

For more details about the different make target

```bash
make help
```

## Runtime environment

| Key | Notes |
|-----|-------|
| **TEMPO_KEY**<br/>(required) | To read data from tempo, the API key to use is expected as the *TEMPO_KEY* environment variable. |
| **TEMPO_CONFIG_PATH**<br/>(optional) | To be able to add secret configurations there is a default config path `/tempo` where secrets can be mounted as files. For development purposes the environment variable *TEMPO_CONFIG_PATH* overrides the default value for config files. |
| **TEMPO_LOG_LEVEL**<br/>(optional) | Tempo uses `logging` for logging, with the default log level `WARNING`. This can be changed by setting the environment variable *TEMPO_LOG_LEVEL* to any value in `["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]` |
| **NOTION_KEY**<br/>(optional) | Notion API key. |
| **NOTION_OKR_DATABASE_ID**<br/>(optional) | *Requires: NOTION_KEY*<br/>The ID for a specific database in Notion, see [this](https://stackoverflow.com/questions/67728038/where-to-find-database-id-for-my-database-in-notion) link. |
| **NOTION_OKR_LABELS**<br/>(optional) | *Requires: NOTION_KEY and NOTION_OKR_DATABASE_ID*<br/>The labels used in Notion. |
| **NOTION_FINANCIAL_DATABASE_ID**<br/>(optional) | *Requires: NOTION_KEY*<br/>Like the example of *NOTION_OKR_DATABASE*, a database ID from notion is needed. The database should include the column names `Month`, `cost`, `total-cost-b2b`, and `total-income`. |
| **NOTION_WORKINGHOURS_DATABASE_ID**<br/>(optional) | *Requires: NOTION_KEY*<br/>Like the example of *NOTION_OKR_DATABASE*, a database ID from notion is needed. The database should include the column names `User`, `Daily`, `Delta`, `Start`, and `Stop`. |
| **NOTION_TASKS_DATABASE_ID**<br/>(optional) | *Requires: NOTION_KEY*<br/>Like the example of *NOTION_OKR_DATABASE*, a database ID from notion is needed. The database should include the column names `TaskID`, `Tags`, `Desc`. |

## Configuration files

Metrics is expecting a simple layout for the optional configuration files. A folder structure found in `/tempo` or, if set, in ${TEMPO_CONFIG_PATH}.

```bash
.
└── rates
    └── data.json
```

### rates

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
    .....
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
    },
    ...
  ],
  "Internal": [
    {
      "Key": "US"
    },
    ...
  ],
  "Currency": [
    {
      "SEK2EUR": "0.1"
    }
  ]
}
```

