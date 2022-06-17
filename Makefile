REPO := europe-north1-docker.pkg.dev/verifa-metrics/docker
TAG := $(shell git describe --tags --always --dirty=-dev)
IMAGE := $(REPO)/metrics-dashboard

CLOUDRUN_SERVICE=metrics-dashboard

DOCKER := docker

default: build

.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<

install:
	poetry install

.PHONY: tests
tests: install
	$(foreach testfile, $(wildcard ./tests/*.py), poetry run python $(testfile);)

.PHONY: black-check
black-check:
	black --check .
	echo ${?}

.PHONY: black
black:
	black .

dev: install black-check
	poetry run python app.py

run: build
	$(DOCKER) run --rm -ti -e TEMPO_KEY=${TEMPO_KEY} --name metrics-dashboard -p 8000:8000 $(IMAGE):$(TAG)

build:
	$(DOCKER) build -t $(IMAGE):$(TAG) .

push: build
	$(DOCKER) push $(IMAGE):$(TAG)
	$(DOCKER) tag $(IMAGE):$(TAG) $(IMAGE):latest
	$(DOCKER) push $(IMAGE):latest

deploy:
	gcloud run deploy $(CLOUDRUN_SERVICE) --image $(IMAGE):$(TAG) --region europe-north1
