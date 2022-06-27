# Default variables
# Dynamic
REGION := europe-north1
REPO := $(REGION)-docker.pkg.dev/verifa-metrics/docker
TAG := $(shell git describe --tags --always --dirty=-dev)
IMAGE := $(REPO)/metrics-dashboard
DOCKER := docker
# Static
CLOUDRUN_SERVICE=metrics-dashboard

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
	$(foreach testfile, $(wildcard ./tests/*.py), poetry run python $(testfile);)

## black-check:
##	checks if black would reformat any file
##
.PHONY: black-check
black-check:
	black --check .

## black:
##	uses black to reformat the python files, if needed
##
.PHONY: black
black:
	black .

## dev:
##	runs app.py locally using poetry
##
##	dependes on install: and black-check:
##
dev: install black-check
	poetry run python app.py

## run:
##	uses $(DOCKER) to run the metrics-dashboard image in a local container
##
##	depends on build:
##	uses $(DOCKER), $(TEMPO_KEY), $(IMAGE) and $(TAG)
##
run: build
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
	gcloud run deploy $(CLOUDRUN_SERVICE) --image $(IMAGE):$(TAG) --region $(REGION)
