REPO := europe-north1-docker.pkg.dev/verifa-metrics/docker
TAG := $(shell git describe --tags --always --dirty=-dev)
IMAGE := $(REPO)/metrics-dashboard

CLOUDRUN_SERVICE=metrics-dashboard

default: build

.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<

build:
	docker build -t $(IMAGE):$(TAG) .

push: build
	docker push $(IMAGE):$(TAG)
	docker tag $(IMAGE):$(TAG) $(IMAGE):latest
	docker push $(IMAGE):latest

deploy:
	gcloud run deploy $(CLOUDRUN_SERVICE) --image $(IMAGE):$(TAG) --region europe-north1
