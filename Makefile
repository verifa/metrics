REPO := europe-north1-docker.pkg.dev/verifa-metrics/docker
TAG := $(shell git describe --tags --always --dirty=-dev)
IMAGE := $(REPO)/metrics-dashboard

CLOUDRUN_SERVICE=metrics-dashboard

default: build

.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<

install:
	poetry install

dev:
	poetry run python app.py

run: build
	docker run --rm -ti --name metrics-dashboard -p 8000:8000 $(IMAGE):$(TAG)

build:
	docker build -t $(IMAGE):$(TAG) .

push: build
	docker push $(IMAGE):$(TAG)
	docker tag $(IMAGE):$(TAG) $(IMAGE):latest
	docker push $(IMAGE):latest

deploy:
	gcloud run deploy $(CLOUDRUN_SERVICE) --image $(IMAGE):$(TAG) --region europe-north1
