import os.path
import tempfile
from pathlib import Path
from typing import List, Optional

import docker
from poetry.toml import TOMLFile


class DockerizeConfiguration:
    name: str = ""
    tags: List[str] = []
    entrypoint_cmd: List[str] = []
    python: str = ""
    ports: List[int] = []
    envs: dict[str, str] = {}
    labels: dict[str, str] = {}


class ProjectConfiguration:
    image_name: str
    image_tags: List[str]
    entrypoint: List[str]
    python_version: str
    ports: List[int] = []
    envs: dict[str, str] = {}
    labels: dict[str, str]


def parse_auto_docker_toml(dict: dict) -> DockerizeConfiguration:
    config = DockerizeConfiguration()
    config.name = dict.get("name")
    tags = dict.get("tags")
    if tags:
        if isinstance(tags, list):
            config.tags = tags
        else:
            config.tags = [tags]

    config.entrypoint_cmd = dict.get("entrypoint")
    config.python = dict.get("python")
    config.ports = dict.get("ports")
    config.envs = dict.get("env")
    config.labels = dict.get("labels")
    return config


def parse_pyproject_toml(pyproject_path) -> ProjectConfiguration:
    pyproject_file = os.path.join(pyproject_path, 'pyproject.toml')
    file = TOMLFile(Path(pyproject_file))
    doc = file.read()

    config = ProjectConfiguration()
    tool = doc.get('tool', dict())
    tool_poetry = tool.get('poetry', dict())

    auto_docker = parse_auto_docker_toml(tool.get('dockerize', dict()))

    config.image_name = auto_docker.name or tool_poetry['name']
    config.image_tags = auto_docker.tags or [tool_poetry["version"], "latest"]

    if auto_docker.entrypoint_cmd:
        config.entrypoint = auto_docker.entrypoint_cmd
    else:
        if 'packages' in tool_poetry:
            packages = tool_poetry['packages']
            if len(packages) > 1:
                raise ValueError('Only one package is supported')
            package = packages[0]
            name = package["include"]
            config.entrypoint = ["python", "-m", name]

    if not config.entrypoint:
        raise ValueError('No package found in pyproject.toml and no entrypoint specified in dockerize section')

    if not auto_docker.python:
        print("No python version specified in dockerize section, using 3.11")
        config.python_version = "3.11"

    config.ports = auto_docker.ports or []
    config.envs = auto_docker.envs or {}
    license = tool_poetry["license"] if "license" in tool_poetry else ""
    repository = tool_poetry["repository"] if "repository" in tool_poetry else ""

    labels = {"org.opencontainers.image.title": config.image_name,
              "org.opencontainers.image.version": tool_poetry["version"],
              "org.opencontainers.image.authors": tool_poetry["authors"],
              "org.opencontainers.image.licenses": license,
              "org.opencontainers.image.url": repository,
              "org.opencontainers.image.source": repository}
    if auto_docker.labels:
        labels.update(auto_docker.labels)
    config.labels = labels

    return config


def generate_docker_file_content(config: ProjectConfiguration) -> str:
    ports_str = ""
    for port in config.ports:
        ports_str += f"EXPOSE {port}\n"

    cmd_str = " ".join(config.entrypoint)
    envs_str = "\n".join([f"ENV {key}={value}" for key, value in config.envs.items()])
    labels_str = "\n".join([f"LABEL {key}={value}" for key, value in config.labels.items()])
    return f"""
FROM python:{config.python_version}-slim-buster as builder
RUN pip install poetry==1.4.2

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

ADD . /app/

RUN cd /app && poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

FROM python:{config.python_version}-slim-buster as runtime

{labels_str}

ENV PATH="/app/.venv/bin:$PATH"
{envs_str}

WORKDIR /app
COPY --from=builder /app/ /app/

{ports_str}                
CMD {cmd_str}"""


def build_image(path: str) -> None:
    config = parse_pyproject_toml(path)
    build(config=config, root_path=path)


def build(
        root_path: str,
        config: ProjectConfiguration
) -> None:
    """
    Build a docker image from a poetry project.
    """

    with tempfile.NamedTemporaryFile() as tmp:
        dockerfile = tmp.name
        content = generate_docker_file_content(config)
        tmp.write(content.encode("utf-8"))
        tmp.flush()
        real_context_path = os.path.realpath(root_path)
        for tag in config.image_tags:
            full_image_name = f"{config.image_name}:{tag}"
            print(f"Building image: {full_image_name}")
            docker_client = docker.from_env()
            docker_client.images.build(
                path=real_context_path,
                dockerfile=dockerfile,
                tag=full_image_name
            )
            print(f"Successfully built image: {full_image_name}")
