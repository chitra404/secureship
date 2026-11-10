IMAGE ?= secureship-api:local

.PHONY: help setup check install test run build docker-run scan sbom clean

help:
	@echo "make setup       create .venv, install, run tests (scripts/setup.sh)"
	@echo "make check       run all pre-push checks (scripts/check.sh)"
	@echo "make install     install app + test dependencies"
	@echo "make test        run the tests"
	@echo "make run         run the API locally on 127.0.0.1:8000"
	@echo "make build       build the Docker image ($(IMAGE))"
	@echo "make docker-run  run the image with hardened settings"
	@echo "make scan        Trivy scan, fails on CRITICAL (needs trivy)"
	@echo "make sbom        write sbom.spdx.json (needs syft)"
	@echo "make clean       remove caches and the virtualenv"

setup:
	./scripts/setup.sh

check:
	./scripts/check.sh

install:
	python3 -m pip install -r requirements-dev.txt

test:
	python3 -m pytest -q

run:
	python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

build:
	docker build -t $(IMAGE) .

docker-run:
	docker run --rm -p 8000:8000 --read-only --cap-drop ALL \
		--security-opt no-new-privileges $(IMAGE)

scan:
	trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 $(IMAGE)

sbom:
	syft $(IMAGE) -o spdx-json=sbom.spdx.json

clean:
	rm -rf .pytest_cache app/__pycache__ tests/__pycache__ .venv sbom.spdx.json trivy-report.txt image.tar
