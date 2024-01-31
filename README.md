# Poetry Dockerize Plugin

<p align="center">
  <a href="https://pypi.org/project/poetry-dockerize-plugin/">
    <img src="https://img.shields.io/pypi/v/poetry-dockerize-plugin?color=green&amp;label=pypi%20package" alt="PyPI">
  </a>
  <a href="https://pepy.tech/project/poetry-dockerize-plugin">
    <img src="https://static.pepy.tech/badge/poetry-dockerize-plugin" alt="Downloads">
  </a>
  <a href="">
    <img src="https://img.shields.io/pypi/pyversions/poetry-dockerize-plugin?color=green" alt="Py versions">
  </a>
</p>


Key features:

* Automatically generate a docker image from your Poetry application.
* Highly configurable. You can configure the image by adding a section in the `pyproject.toml` configuration file.

## Installation

In order to install the plugin you need to have installed a poetry version `>=1.2.0` and type:

```bash
poetry self add poetry-dockerize-plugin
```

## Quickstart

No configuration needed! Just type:
```bash
poetry dockerize
>Building image: poetry-sample-app:latest
>Successfully built image: poetry-sample-app:latest
docker run --rm -it poetry-sample-app:latest
>hello world!
```

### Usage in GitHub Actions
You just need to run the quickstart command in your GitHub Actions workflow:
```yaml

name: Build and publish latest

on:
  push:
    branches: main

jobs:
  login:
    runs-on: ubuntu-latest
    steps:
        - name: Install Poetry
          uses: snok/install-poetry@v1

        - name: Install poetry-dockerize-plugin
          run: poetry self add poetry-dockerize-plugin

        - name: Build and package
          run: |
            poetry install
            poetry run pytest
            poetry dockerize

        - name: Login to Docker Hub
          uses: docker/login-action@v3
          with:
            username: ${{ secrets.DOCKERHUB_USERNAME }}
            password: ${{ secrets.DOCKERHUB_TOKEN }}

        - name: Push to Docker Hub
          run: docker push my-app:latest
```

## Configuration
To customize some options, you can add a `[tool.dockerize]` section in your `pyproject.toml` file. For example to change the image name:

```toml
[tool.dockerize]
name = "myself/myproject-app"
```

## Configuration API Reference

This examples shows a complete configuration of the docker image:

```toml
[tool.docker]
name = "alternative-image-name"
python = "3.12"
base-image = "python:3.12-slim"
tags = ["latest-dev"]
entrypoint = ["python", "-m", "whatever"]
ports = [5000]
env = {"MY_APP_ENV" = "dev"}
labels = {"MY_APP_LABEL" = "dev"}
apt-packages = ["curl"]
extra-build-instructions = ["RUN poetry config http-basic.foo <username> <password>"]
extra-run-instructions = ["RUN curl https://huggingface.co/transformers/"]
```

* `name` customizes the docker image name. 
* `python` python version to use. If not specified, will try to be extracted from `tool.poetry.dependencies.python`. Default is `3.11`
* `base-image` customizes the base image. If not defined, the default base image is `python:<python-version>-slim-buster`. 
* `tags` declares a list of tags for the image.
* `entrypoint` customizes the entrypoint of the image. If not provided, the default entrypoint is retrieved from the `packages` configuration.
* `ports` exposes ports
* `env` declares environment variables inside the docker image.
* `labels` append labels to the docker image. Default labels are added following the opencontainers specification.
* `apt-packages` installs apt packages inside the docker image.
* `extra-build-instructions` adds extra instructions to the docker build (before poetry install). Any modification to the filesystem will be lost after the poetry install. If you need to add files to the image, use the `extra-run-instructions`.
* `extra-run-instructions` adds extra instructions to the docker run (after poetry install). Any modification to the filesystem will be kept after the poetry install.


## Command-Line options

All command line options provided by the `poetry-dockerize-plugin` may be accessed by typing:

```bash
poetry dockerize --help
```

## Troubleshooting

To troubleshoot the plugin, you can use the `--debug` flag to get more information about the execution.

```bash
poetry dockerize --debug
```

## License

This project is licensed under the terms of the MIT license.
