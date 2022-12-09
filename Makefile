# Default variables
# Dynamic
REGION := europe-north1
REPO := $(REGION)-docker.pkg.dev/verifa-metrics/docker
TAG := $(shell git describe --tags --always --dirty=-dev)
IMAGE := $(REPO)/metrics-dashboard
DOCKER := docker
PIP := pip3

# Static
CLOUDRUN_SERVICE=metrics-dashboard
MAKEFLAGS += -j2

##
## 		Makefile targets
## 		----------------
##

## default:
## 	build: is the default target
##
default: build

## help:
## 	prints this help
##
.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<

## vars:
##	prints the variables used in this Makefile
##
.PHONY: vars
vars:
	@echo ""
	$(foreach v, $(.VARIABLES), $(if $(filter file,$(origin $(v))), $(info $(v)=$($(v)))))

## install:
## 	installs the dependencies with potry
##
install:
	poetry install

## tests:
##	runs all python files in the tests folder
##
.PHONY: tests
tests: install
	poetry run python -m unittest discover

## black-check:
##	checks if black would reformat any file
##
.PHONY: black-check
black-check:
	$(PIP) install black > black-install.log
	black --check .

## black:
##	uses black to reformat the python files, if needed
##
.PHONY: black
black:
	$(PIP) install black > black-install.log
	black .

## isort
##	uses isort to check the import declarations
.PHONY: isort
isort:
	$(PIP) install black > black-install.log
	isort . -c --diff

## mypy
##	uses mypy to check the project
.PHONY: mypy
mypy:
	$(PIP) install mypy > mypy-install.log
	mypy .

## pylint
##	uses pylint to lint the files
##
.PHONY: pylint
pylint:
	$(PIP) install pylint > pylint-install.log
	pylint .

## lint:
##	a PHONY rule to run all linters
##
.PHONY: lint
lint: black-check pylint mypy isort

## dev:
##	runs app.py locally using poetry
##
##	dependes on install: and black-check:
##
dev: install lint tests
	poetry run python app.py

## run:
##	uses $(DOCKER) to run the metrics-dashboard image in a local container
##
##  if $(TEMPO_CONFIG_PATH) is set, this is mounted as /tempo in the container
##
##	depends on build:
##	uses $(DOCKER), $(TEMPO_KEY), $(IMAGE) and $(TAG)
##
ifneq ($(TEMPO_CONFIG_PATH),)
  vmounts=-v $(TEMPO_CONFIG_PATH):/tempo
else
  vmounts=
endif


run: build
	$(info Additional docker mounts: $(vmounts))
	$(DOCKER) run --rm -ti -e TEMPO_KEY=${TEMPO_KEY} $(vmounts) --name metrics-dashboard -p 8000:8000 $(IMAGE):$(TAG)

## bare:
##	uses $(DOCKER) to run the metrics-dashboard image in a local container
##  without any optional config files
##
##	depends on build:
##	uses $(DOCKER), $(TEMPO_KEY), $(IMAGE) and $(TAG)
##
bare: build
	$(DOCKER) run --rm -ti -e TEMPO_KEY=${TEMPO_KEY} --name metrics-dashboard -p 8000:8000 $(IMAGE):$(TAG)

## build:
##	builds the metrics-dashboard image
##
##	uses $(DOCKER), $(IMAGE) and $(TAG)
##
build:
	$(DOCKER) build -t $(IMAGE):$(TAG) .

## push:
##	pushes the image
##
##	depends on build:
##	uses $(DOCKER), $(IMAGE) and $(TAG)
##
push: build
	$(DOCKER) push $(IMAGE):$(TAG)
	$(DOCKER) tag $(IMAGE):$(TAG) $(IMAGE):latest
	$(DOCKER) push $(IMAGE):latest

## deploy:
##	deploys the built image to google cloud
##
deploy:
	gcloud run deploy $(CLOUDRUN_SERVICE) --image $(IMAGE):$(TAG) --region $(REGION) --labels=version=$(TAG)
