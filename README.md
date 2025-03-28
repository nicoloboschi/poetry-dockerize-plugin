# Dockerpyze (dpy)

> Previously named poetry-dockerize-plugin

<p align="center">
    <img src="https://raw.githubusercontent.com/nicoloboschi/dockerpyze/refs/heads/main/dockerpyze.webp" alt="PyPI">
</p>


<p align="center">
  <a href="https://pypi.org/project/dockerpyze/">
    <img src="https://img.shields.io/pypi/v/dockerpyze?color=green&amp;label=pypi%20package" alt="PyPI">
  </a>
  <a href="https://pepy.tech/project/poetry-dockerize-plugin">
    <img src="https://static.pepy.tech/badge/poetry-dockerize-plugin" alt="Downloads">
  </a>
  <a href="">
    <img src="https://img.shields.io/pypi/pyversions/dockerpyze?color=green" alt="Py versions">
  </a>
</p>


**Key features**:

* Automatically generate a docker image from your `uv`/`poetry` application.
* PEP-621 compliant.
* 100% configurable. You can configure the image by adding a section in the `pyproject.toml` configuration file.

## Quickstart

### uv
1. Install it as a dev dependency:
```
uv add dockerpyze --dev
```
2. Configure entrypoint in `pyproject.toml`:
```toml
[tool.dpy]
entrypoint = "uv run <your-script>"
```
3. Now straight to the point:
```bash
uv run dockerpyze
>No .dockerignore found, using a good default one 😉
>Building image: dockerpyze:latest 🔨
Successfully built images: ✅  (0.3s)
  - dockerpyze:latest
```
4. Tell your friends about this library 😉


### poetry
0. Move your project to `uv`... well if you can't do it, you can still use `poetry`.
1. Install the freaking plugin:
```
poetry self add dockerpyze@latest
```
2. Configure entrypoint in `pyproject.toml`:
```toml
[tool.dpy]
entrypoint = "poetry run <your-script>"
```
3. Now straight to the point:
```bash
poetry dockerpyze
>No .dockerignore found, using a good default one 😉
>Building image: dockerpyze:latest 🔨
Successfully built images: ✅  (0.3s)
  - dockerpyze:latest
```
4. Tell your friends about this library 😉 (and then switch to `uv`)

## Configuration via pyproject.toml
To customize some options, you can add a `[tool.dpy]` section in your `pyproject.toml` file. For example to change the image name:

```toml
[tool.dpy]
name = "myself/myproject-app"
```

## Configuration via environment variables
You can also pass any option via environment variable by prefixing the key with `DPY_`. For example, to set the `entrypoint` you can use the `DPY_ENTRYPOINT` environment variable:

```bash
export DPY_ENTRYPOINT="python -m myapp"
uv run dockerpyze
```

or use a .env file which will be loaded by the plugin:
```
echo "DPY_ENTRYPOINT=python -m myapp" > .env
poetry dockerpyze
```

For dicts such as `env` and `labels`, you can set multiple values by adding multiple variables:

```bash
export DPY_ENV_MY_VAR="my_value"
export DPY_ENV_MY_OTHER_VAR="my_other_value"
export DPY_LABELS_MY_LABEL="label1"
poetry dockerpyze
```

## Usage in GitHub Actions
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
        - name: Check out the repo
          uses: actions/checkout@v3

        - name: "Setup: Python 3.11"
          uses: actions/setup-python@v4

        - name: Install uv
          run: python -m pip install uv

        - name: Build and package
          run: |
            uv sync
            uv run ruff 
            uv run pytest
            uv run dockerpyze

        - name: Login to Docker Hub
          uses: docker/login-action@v3
          with:
            username: ${{ secrets.DOCKERHUB_USERNAME }}
            password: ${{ secrets.DOCKERHUB_TOKEN }}

        - name: Push to Docker Hub
          run: docker push my-app:latest
```



## Configuration API Reference

This examples shows a complete configuration of the docker image:

```toml
[tool.dpy]
name = "alternative-image-name"
python = "3.12"
base-image = "python:3.12-slim"
tags = ["latest-dev"]
entrypoint = ["python", "-m", "whatever"]
ports = [5000]
env = {"MY_APP_ENV" = "dev"}
labels = {"MY_APP_LABEL" = "dev"}
apt-packages = ["curl"]
extra-run-instructions = ["RUN curl https://huggingface.co/transformers/"]

# Only for build docker layer
build-apt-packages = ["gcc"]
extra-build-instructions = ["RUN poetry config http-basic.foo <username> <password>"]
build-poetry-install-args = ["-E", "all", "--no-root"]

```

* `name` customizes the docker image name. 
* `python` python version to use. If not specified, will try to be extracted from `tool.poetry.dependencies.python`. Default is `3.11`
* `base-image` customizes the base image. If not defined, the default base image is `python:<python-version>-slim-bookworm`. 
* `tags` declares a list of tags for the image.
* `entrypoint` customizes the entrypoint of the image. If not provided, the default entrypoint is retrieved from the `packages` configuration.
* `ports` exposes ports
* `env` declares environment variables inside the docker image.
* `labels` append labels to the docker image. Default labels are added following the opencontainers specification.
* `apt-packages` installs apt packages inside the docker image.
* `extra-run-instructions` adds extra instructions to the docker run (after poetry install). Any modification to the filesystem will be kept after the poetry install.

For the build step:
* `build-apt-packages` installs apt packages inside the build docker container.
* `extra-build-instructions` adds extra instructions to the docker build (before poetry install). Any modification to the filesystem will be lost after the poetry install. If you need to add files to the image, use the `extra-run-instructions`.
* `build-poetry-install-args` adds additional arguments to the `poetry install` command in the build step.


## Command line options

All command line options provided by the `dockerpyze` may be accessed by typing:

```bash
uv run dockerpyze --help
poetry dockerpyze --help
```

## Troubleshooting

To troubleshoot the plugin, you can use the `--debug` flag to get more information about the execution.

```bash
poetry dockerpyze --debug
```

The build is broken and `--debug` is completely useless? I get it. 
You can generate the `Dockerfile` and manually build it to have more control over the problem.
```
uv run dockerpyze --generate
docker build Dockerfile .
```

>It's totally fine to use the `--generate` flag to generate the initial `Dockerfile` and then customize it. I don't mind.

## License

This project is licensed under the terms of the MIT license.

## Issues or want to contribute?
1. Open an issue 
2. (optional) Open a pull request and I'll merge it, maybe.
