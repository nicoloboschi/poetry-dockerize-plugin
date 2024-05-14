import os
import tempfile

from poetry_dockerize_plugin.builder import build_image, parse_pyproject_toml, generate_docker_file_content, \
    ProjectConfiguration

dirname = os.path.dirname(__file__)
test_project = os.path.join(dirname, 'test_project')


def _parse_pyproject_toml_content(content: str) -> ProjectConfiguration:
    tempdir = tempfile.TemporaryDirectory()
    with open(os.path.join(tempdir.name, "pyproject.toml"), 'w') as f:
        f.write(content)
    return parse_pyproject_toml(tempdir.name)


def test() -> None:
    clean_dockerfile()
    build_image(path=test_project)
    assert os.path.exists(os.path.join(test_project, "Dockerfile")) is False


def test_and_generate() -> None:
    clean_dockerfile()
    build_image(path=test_project, generate=True)
    assert os.path.exists(os.path.join(test_project, "Dockerfile")) is True


def clean_dockerfile():
    file = os.path.join(test_project, "Dockerfile")
    if os.path.exists(file):
        os.remove(file)


def test_parse_entrypoint() -> None:
    doc = _parse_pyproject_toml_content("""
[tool.poetry]
name = "my-app"
version = "0.1.0"
packages = [{include = "app"}]
    """)

    assert doc.entrypoint == ['python', '-m', 'app']


def test_parse_custom_entrypoint() -> None:
    doc = _parse_pyproject_toml_content("""
[tool.poetry]
name = "my-app"
version = "0.1.0"
packages = [{include = "app"}]
[tool.dockerize]
entrypoint = "uvicorn app.main:app --host"
    """)

    assert doc.entrypoint == ["uvicorn", "app.main:app", "--host"]


def test_parse_entrypoint_with_multiple_packages() -> None:
    try:
        _parse_pyproject_toml_content("""
[tool.poetry]
name = "my-app"
version = "0.1.0"
packages = [{include = "app"}, {include = "app2"}]
    """)
    except Exception as e:
        assert str(e) == """Multiple 'packages' found in pyproject.toml, please specify 'entrypoint' in 'tool.dockerize' section.
[tool.dockerize] 
entrypoint = "python -m app"
"""
        doc = _parse_pyproject_toml_content("""
        [tool.poetry]
        name = "my-app"
        version = "0.1.0"
        packages = [{include = "app"}, {include = "app2"}]
        [tool.dockerize]
        entrypoint = "python -m app2"
""")
        assert doc.entrypoint == ["python", "-m", "app2"]


def test_parse_pyversion() -> None:
    doc = _parse_pyproject_toml_content("""
[tool.poetry]
name = "my-app"
version = "0.1.0"
packages = [{include = "app"}]
    """)
    assert doc.base_image == "python:3.11-slim-buster"
    doc = _parse_pyproject_toml_content("""
    [tool.poetry]
    name = "my-app"
    version = "0.1.0"
    packages = [{include = "app"}]
    [tool.poetry.dependencies]
    python = "^3.9"
""")
    assert doc.base_image == "python:3.9-slim-buster"
    doc = _parse_pyproject_toml_content("""
        [tool.poetry]
        name = "my-app"
        version = "0.1.0"
        packages = [{include = "app"}]
        [tool.poetry.dependencies]
        python = ">3.9,<3.12"
    """)
    assert doc.base_image == "python:3.11-slim-buster"


def test_parse() -> None:
    config = parse_pyproject_toml(test_project)
    content = generate_docker_file_content(config, test_project)
    print(content)
    assert content == """
FROM python:3.11-slim-buster as builder
RUN pip install poetry==1.7.1

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache
RUN poetry config virtualenvs.create false && poetry config virtualenvs.in-project false


ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'Acquire::http::Timeout "30";\\nAcquire::http::ConnectionAttemptDelayMsec "2000";\\nAcquire::https::Timeout "30";\\nAcquire::https::ConnectionAttemptDelayMsec "2000";\\nAcquire::ftp::Timeout "30";\\nAcquire::ftp::ConnectionAttemptDelayMsec "2000";\\nAcquire::Retries "15";' > /etc/apt/apt.conf.d/99timeout_and_retries \
     && apt-get update \
     && apt-get -y dist-upgrade \
     && apt-get -y install git
RUN mkdir /app
COPY pyproject.toml /app/pyproject.toml


COPY ./app /app/app

RUN poetry -V

RUN cd /app && poetry install --no-interaction --no-ansi --no-root

FROM python:3.11-slim-buster as runtime

ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'Acquire::http::Timeout "30";\\nAcquire::http::ConnectionAttemptDelayMsec "2000";\\nAcquire::https::Timeout "30";\\nAcquire::https::ConnectionAttemptDelayMsec "2000";\\nAcquire::ftp::Timeout "30";\\nAcquire::ftp::ConnectionAttemptDelayMsec "2000";\\nAcquire::Retries "15";' > /etc/apt/apt.conf.d/99timeout_and_retries \
     && apt-get update \
     && apt-get -y dist-upgrade \
     && apt-get -y install curl
LABEL org.opencontainers.image.title=poetry-sample-app
LABEL org.opencontainers.image.version=0.1.0
LABEL org.opencontainers.image.authors=['Nicolò Boschi <boschi1997@gmail.com>']
LABEL org.opencontainers.image.licenses=
LABEL org.opencontainers.image.url=
LABEL org.opencontainers.image.source=

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PORT=5001

WORKDIR /app
COPY --from=builder /app/ /app/

EXPOSE 5001
RUN echo 'Hello from Dockerfile' > /tmp/hello.txt
CMD python -m app"""
