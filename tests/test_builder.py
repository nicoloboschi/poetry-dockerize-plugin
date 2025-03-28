import os
import tempfile

from dockerpyze.builder import build_image, parse_pyproject_toml, generate_docker_file_content, \
    ProjectConfiguration

dirname = os.path.dirname(__file__)
test_project = os.path.join(dirname, 'test_project')
dummy_project = os.path.join(dirname, 'dummy_project')


def _parse_pyproject_toml_content(content: str) -> ProjectConfiguration:
    tempdir = tempfile.TemporaryDirectory()
    with open(os.path.join(tempdir.name, "pyproject.toml"), 'w') as f:
        f.write(content)
    return parse_pyproject_toml(tempdir.name)


def test() -> None:
    clean_dockerfile()
    build_image(path=test_project)
    assert os.path.exists(os.path.join(test_project, "Dockerfile")) is False
    import docker
    docker_client = docker.from_env()
    docker_client.containers.run("poetry-sample-app:0.1.0", detach=True, command="sample-cli")


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


def test_parse_custom_entrypoint_shell_format() -> None:
    doc = _parse_pyproject_toml_content("""
[tool.poetry]
name = "my-app"
version = "0.1.0"
packages = [{include = "app"}]
[tool.dpy]
entrypoint = "uvicorn app.main:app --host"
    """)

    assert doc.entrypoint == ["uvicorn app.main:app --host"]


def test_parse_custom_entrypoint_exec_format() -> None:
    doc = _parse_pyproject_toml_content("""
    [tool.poetry]
    name = "my-app"
    version = "0.1.0"
    packages = [{include = "app"}]
    [tool.dpy]
    entrypoint = ["uvicorn", "app.main:app", "--host"]
        """)
    assert doc.entrypoint == ["uvicorn", "app.main:app", "--host"]


def test_parse_custom_entrypoint_exec_format() -> None:
    doc = _parse_pyproject_toml_content("""
    [tool.poetry]
    name = "my-app"
    version = "0.1.0"
    packages = [{include = "app"}]
    [tool.dpy]
    entrypoint = ["uvicorn", "app.main:app", "--host"]
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
        assert str(e) == """Multiple 'packages' found in pyproject.toml, please specify 'entrypoint' in 'tool.dpy' section.
[tool.dpy] 
entrypoint = "python -m app"
"""
        doc = _parse_pyproject_toml_content("""
        [tool.poetry]
        name = "my-app"
        version = "0.1.0"
        packages = [{include = "app"}, {include = "app2"}]
        [tool.dpy]
        entrypoint = "python -m app2"
""")
        assert len(doc.entrypoint) == 1
        assert doc.entrypoint[0] == "python -m app2"


def test_parse_pyversion() -> None:
    doc = _parse_pyproject_toml_content("""
[project]
name = "my-app"
version = "0.1.0"
[tool.dpy]
entrypoint = "uvicorn app.main:app --host"
    """)
    assert doc.base_image == "python:3.11-slim-bookworm"
    doc = _parse_pyproject_toml_content("""
    [project]
    name = "my-app"
    version = "0.1.0"
    requires-python = "^3.9"
    [tool.dpy]
    entrypoint = "uvicorn app.main:app --host"
""")
    assert doc.base_image == "python:3.9-slim-bookworm"
    doc = _parse_pyproject_toml_content("""
        [project]
        name = "my-app"
        version = "0.1.0"
        requires-python = "^3.11"
        [tool.dpy]
        entrypoint = "uvicorn app.main:app --host"
    """)
    assert doc.base_image == "python:3.11-slim-bookworm"


def test_parse_poetry_version_hardcoded() -> None:
    # Fallback to hardcoded version, no lock file nor version specified in pyproject.toml
    doc = _parse_pyproject_toml_content("""
    [tool.poetry]
    name = "my-app"
    version = "0.1.0"
    packages = [{include = "app"}]
    [tool.poetry.dependencies]
    httpx = "^0.19.0"
        """)
    assert doc.poetry_version == "1.8.3"


def test_parse_poetry_version_pyproject() -> None:
    # Use version in pyproject.toml
    doc = _parse_pyproject_toml_content("""
    [tool.poetry]
    name = "my-app"
    version = "0.1.0"
    packages = [{include = "app"}]
    [tool.dpy]
    poetry-version = "1.7.1"
    [tool.poetry.dependencies]
    httpx = "^0.19.0"
        """)
    assert doc.poetry_version == "1.7.1"


def test_parse_poetry_version_lock_file() -> None:
    # No explicit version, but lock file is present
    doc_from_lock = parse_pyproject_toml(dummy_project)
    # POETRY_VERSION set in workflow, fallback to 1.8.3 if not set
    expected_poetry_version = os.getenv("POETRY_VERSION", "1.8.3")
    assert doc_from_lock.poetry_version == expected_poetry_version


def test_parse() -> None:
    config = parse_pyproject_toml(test_project)
    content = generate_docker_file_content(config, test_project)
    print(content)
    assert content == """
FROM python:3.11-slim-bookworm AS builder
RUN pip install poetry==1.8.2

ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache



ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'Acquire::http::Timeout "30";\\nAcquire::http::ConnectionAttemptDelayMsec "2000";\\nAcquire::https::Timeout "30";\\nAcquire::https::ConnectionAttemptDelayMsec "2000";\\nAcquire::ftp::Timeout "30";\\nAcquire::ftp::ConnectionAttemptDelayMsec "2000";\\nAcquire::Retries "15";' > /etc/apt/apt.conf.d/99timeout_and_retries \
     && apt-get update \
     && apt-get -y dist-upgrade \
     && apt-get -y install gcc git
RUN mkdir /app
COPY pyproject.toml poetry.lock* uv.lock* README* /app/


COPY ./app /app/app

RUN poetry -V

RUN cd /app && poetry install --no-interaction --no-ansi -E ext

FROM python:3.11-slim-bookworm AS runtime

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
CMD ["python", "-m", "app"]"""


def test_parse_from_env() -> None:
    try:
        os.environ["DPY_ENTRYPOINT"] = "uvicorn app.main:app --host"
        os.environ["DPY_BASE_IMAGE"] = "python:3.9-slim"
        os.environ["DPY_PORTS"] = "5000 5001"
        os.environ["DPY_ENV_VAR1"] = "VALUE1"
        os.environ["DPY_ENV_VAR2"] = "VALUE2"
        doc = _parse_pyproject_toml_content("""
    [tool.poetry]
    name = "my-app"
    version = "0.1.0"
        """)

        assert len(doc.entrypoint) == 1
        assert doc.entrypoint[0] == "uvicorn app.main:app --host"
        assert doc.base_image == "python:3.9-slim"
        assert doc.ports == [5000, 5001]
        assert doc.envs == {"VAR1": "VALUE1", "VAR2": "VALUE2"}
    finally:
        os.environ.pop("DPY_ENTRYPOINT")
        os.environ.pop("DPY_BASE_IMAGE")
        os.environ.pop("DPY_PORTS")
        os.environ.pop("DPY_ENV_VAR1")
        os.environ.pop("DPY_ENV_VAR2")
