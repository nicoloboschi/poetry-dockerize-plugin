import argparse
import os.path
import re
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import List, Optional, Any, Literal

import docker
from docker.errors import BuildError

from dotenv import load_dotenv
load_dotenv()


class DpyConfiguration:
    name: str = ""
    tags: List[str] = []
    entrypoint_cmd: List[str] = []
    python: str = ""
    ports: List[int] = []
    envs: dict[str, str] = {}
    labels: dict[str, str] = {}
    apt_packages: List[str] = []
    build_apt_packages: List[str] = []
    build_poetry_install_args: List[str] = []
    base_image: str = ""
    extra_build_instructions: List[str] = []
    extra_runtime_instructions: List[str] = []
    poetry_version: str = ""


class ProjectConfiguration:
    image_name: str
    image_tags: List[str]
    entrypoint: List[str]
    ports: List[int] = []
    envs: dict[str, str] = {}
    labels: dict[str, str]
    build_apt_packages: List[str] = []
    build_poetry_install_args: List[str] = []
    runtime_apt_packages: List[str] = []
    base_image: str = ""
    extra_build_instructions: List[str] = []
    extra_runtime_instructions: List[str] = []
    deps_packages: List[str] = []
    app_packages: List[str] = []
    poetry_version: str = ""
    package_manager: Literal["uv", "poetry"]



def _parse_list_str(value: Any, split_by: Optional[str] = " ") -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if split_by is not None:
        return str(value).split(split_by)
    return [str(value)]


def parse_toml(from_dict: dict) -> DpyConfiguration:
    config = DpyConfiguration()
    config.name = _from_env_or_dict_str("name", from_dict)
    config.tags = _from_env_or_dict_list_str("tags", from_dict)
    config.entrypoint_cmd = _from_env_or_dict_list_str("entrypoint", from_dict)
    config.python = _from_env_or_dict_str("python", from_dict)
    config.ports = _from_env_or_dict_list_int("ports", from_dict)
    config.envs = _from_env_or_dict_to_dict("env", from_dict)
    config.labels = _from_env_or_dict_to_dict("labels", from_dict)
    config.apt_packages = _from_env_or_dict_list_str("apt-packages", from_dict)
    config.build_apt_packages = _from_env_or_dict_list_str("build-apt-packages", from_dict)
    config.build_poetry_install_args = _from_env_or_dict_list_str("build-poetry-install-args", from_dict)
    config.base_image = _from_env_or_dict_str("base-image", from_dict)
    config.extra_build_instructions = _from_env_or_dict_list_str("extra-build-instructions", from_dict)
    config.extra_runtime_instructions = _from_env_or_dict_list_str("extra-runtime-instructions", from_dict)
    config.poetry_version = _from_env_or_dict_str("poetry-version", from_dict)
    return config


def _from_env_or_dict_str(key: str, from_dict: dict) -> str:
    raw_value = _from_env_or_dict_raw(from_dict, key)
    if raw_value is None:
        return ""
    return str(raw_value)

def _from_env_or_dict_list_str(key: str, from_dict: dict, split_by: Optional[str] = None) -> List[str]:
    raw_value = _from_env_or_dict_raw(from_dict, key)
    return _parse_list_str(raw_value, split_by)

def _from_env_or_dict_list_int(key: str, from_dict: dict) -> List[int]:
    raw_value = _from_env_or_dict_raw(from_dict, key)
    as_strings = _parse_list_str(raw_value)
    return [int(s) for s in as_strings]


def _from_env_or_dict_to_dict(key: str, from_dict: dict) -> dict[str, str]:
    to_dict = {}
    from_dict_value = from_dict.get(key)
    if from_dict_value is not None:
        to_dict.update(from_dict_value)

    env_keys = _env_keys(key)
    for env_key in env_keys:
        for env_var in os.environ:
            if env_var.startswith(env_key):
                key = env_var.replace(env_key + "_", "")
                value = os.environ[env_var]
                to_dict[key] = value
    return to_dict

def _from_env_or_dict_raw(from_dict, key) -> Any:
    env_keys = _env_keys(key)
    raw_value = None
    for env_key in env_keys:
        raw_value = os.environ.get(env_key)
        if raw_value:
            break
    if not raw_value:
        raw_value = from_dict.get(key)
    return raw_value


def _env_keys(key):
    formatted = key.upper().replace("-", "_")
    return [f"DOCKERIZE_{formatted}", f"DPY_{formatted}", f"DOCKERPYZE_{formatted}"]


def extract_python_version(pyversion: str) -> Optional[str]:
    try:
        if pyversion == "*":
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            print(f"Python version is too generic (*), using same as system: {python_version}")
        elif re.match("[\\^~]?(\\d\\.\\d+)(\\.\\d+)?", pyversion) is not None:
            python_version = re.match("[\\^~]?(\\d\\.\\d+)(\\.\\d+)?", pyversion).group(1)
        else:
            python_version = re.match("[\\^~]?(\\d)(\\.\\*)?", pyversion).group(1)
        return python_version
    except Exception:
        return None


def extract_poetry_version(pyproject_path) -> str:
    poetry_version = "1.8.3"
    try:
        poetry_lock_path = Path(pyproject_path).joinpath("poetry.lock")
        if poetry_lock_path.exists():
            # search for "@generated by Poetry <version>" in first line
            with poetry_lock_path.open("r") as f:
                first_line = f.readline()
                match = re.search(r"@generated by Poetry (\d+\.\d+\.\d+)", first_line)
                if match:
                    poetry_version = match.group(1)
                else:
                    raise ValueError("Poetry version not found in poetry.lock file")
    except Exception as e:
        if isinstance(e, IOError) or isinstance(e, ValueError):
           print(f"⚠️ Could not read version from poetry.lock file, falling back to hardcoded version {poetry_version}. Got error: {e}")
        else:
            raise e
    return poetry_version


def parse_pyproject_toml(pyproject_path) -> ProjectConfiguration:
    pyproject_file = os.path.join(pyproject_path, 'pyproject.toml')
    if not os.path.exists(pyproject_file):
        raise ValueError(f"pyproject.toml not found, expected to be: {pyproject_file}")
    with open(pyproject_file, "rb") as f:
        doc = tomllib.load(f)

    config = ProjectConfiguration()
    tool = doc.get('tool', dict())
    tool_poetry = tool.get('poetry', dict())
    project = doc.get('project', dict())

    dpy_section_dict = tool.get("dpy", dict()) if "dpy" in tool else tool.get('dockerize', dict())
    dpy_section = parse_toml(dpy_section_dict)

    poetry_deps = tool_poetry.get("dependencies", dict())
    uv_lock = Path(pyproject_path).joinpath("uv.lock")
    poetry_lock = Path(pyproject_path).joinpath("poetry.lock")
    if uv_lock.exists():
        config.package_manager = "uv"
    elif poetry_lock.exists():
        config.package_manager = "poetry"
    else:
        if poetry_deps:
            config.package_manager = "poetry"
        else:
            config.package_manager = "uv"
    if config.package_manager == "uv":
        print("Using 'uv' as package manager ⚡️")
    else:
        print("Using 'poetry' as package manager 🚀")
    if config.package_manager == "poetry":
        if dpy_section.poetry_version:
            config.poetry_version = dpy_section.poetry_version
        else:
            # use the same version as the one used to generate the lock file
            config.poetry_version = extract_poetry_version(pyproject_path)
    config_name = tool_poetry.get('name') or project.get('name')
    config_version = tool_poetry.get('version') or project.get('version')
    config.image_name = dpy_section.name or config_name
    config.image_tags = dpy_section.tags or [config_version, "latest"]

    if dpy_section.entrypoint_cmd:
        config.entrypoint = dpy_section.entrypoint_cmd
    else:
        if 'packages' in tool_poetry:
            packages = tool_poetry['packages']
            if len(packages) > 1:
                raise ValueError(f"""Multiple 'packages' found in pyproject.toml, please specify 'entrypoint' in 'tool.dpy' section.
[tool.dpy] 
entrypoint = "python -m {packages[0]['include']}"
""")
            package = packages[0]
            name = package["include"]
            config.entrypoint = ["python", "-m", name]
        else:
            config.entrypoint = []

    if not config.entrypoint:
        raise ValueError('No package found in pyproject.toml and no entrypoint specified in dpy section')

    config.runtime_apt_packages = dpy_section.apt_packages or []
    config.build_apt_packages = dpy_section.build_apt_packages or []
    config.build_apt_packages.append("gcc")
    config.build_poetry_install_args = dpy_section.build_poetry_install_args or []

    scripts = project.get("scripts", dict())

    for script_name, script_cmd in scripts.items():
        script_cmd_package = script_cmd.split(".")[0]
        config.app_packages.append(script_cmd_package)

    if 'packages' in tool_poetry:
        config.app_packages += [package["include"] for package in tool_poetry['packages']]


    if poetry_deps:
        for dep in poetry_deps:
            if isinstance(tool_poetry["dependencies"][dep], dict):
                if 'path' in tool_poetry["dependencies"][dep]:
                    config.deps_packages.append(tool_poetry["dependencies"][dep]['path'])
                if 'git' in tool_poetry["dependencies"][dep]:
                    config.build_apt_packages.append("git")

    if dpy_section.base_image:
        config.base_image = dpy_section.base_image
    elif not dpy_section.python:
        if ("dependencies" not in tool_poetry or "python" not in tool_poetry["dependencies"]) and ("requires-python" not in project):
            print("No python version specified in pyproject.toml, using 3.11")
            python_version = "3.11"
        else:
            if "dependencies" in tool_poetry and "python" in tool_poetry["dependencies"]:
                declared_py_version = tool_poetry["dependencies"]["python"]
            else:
                declared_py_version = project["requires-python"]
            python_version = extract_python_version(declared_py_version)
            if python_version is None:
                python_version = "3.11"
                print(f"Declared python version dependency is too complex, using default: {python_version}")
            else:
                print(f"Python version extracted from project configuration: {python_version}")
        config.base_image = f"python:{python_version}-slim-bookworm"
    else:
        config.base_image = f"python:{dpy_section.python}-slim-buster"

    config.ports = dpy_section.ports or []
    config.envs = dpy_section.envs or {}
    license = tool_poetry.get("license") or project.get("license", "")
    repository = tool_poetry.get("repository") or project.get("urls", dict()).get("repository", "")
    authors = tool_poetry.get("authors", [])
    if len(authors) == 0:
        # flatten authors dict from PyPA specs to string
        authors = []
        for author in project.get("authors", []):
            if "name" in author and "email" in author:
                author_string = f"{author['name']} <{author['email']}>"
            else:
                author_string = f"{author.get('name', '')}{author.get('email', '')}"
            authors.append(author_string)

    labels = {"org.opencontainers.image.title": config.image_name,
              "org.opencontainers.image.version": config_version,
              "org.opencontainers.image.authors": authors,
              "org.opencontainers.image.licenses": license,
              "org.opencontainers.image.url": repository,
              "org.opencontainers.image.source": repository}
    if dpy_section.labels:
        labels.update(dpy_section.labels)
    config.labels = labels
    config.build_runtime_packages = dpy_section.apt_packages or []
    config.extra_build_instructions = dpy_section.extra_build_instructions or []
    config.extra_runtime_instructions = dpy_section.extra_runtime_instructions or []


    return config


def generate_extra_instructions_str(instructions: List[str]) -> str:
    if not len(instructions):
        return ""
    return "\n".join(instructions)

def _remove_duplicates(lst: List[str]) -> List[str]:
    # remove duplicates while keeping order
    return list(dict.fromkeys(lst))

def generate_apt_packages_str(apt_packages: List[str]) -> str:
    if not len(apt_packages):
        return ""
    apt_packages_str = " ".join(_remove_duplicates(apt_packages))
    return f"""
ARG DEBIAN_FRONTEND=noninteractive

RUN echo 'Acquire::http::Timeout "30";\\nAcquire::http::ConnectionAttemptDelayMsec "2000";\\nAcquire::https::Timeout "30";\\nAcquire::https::ConnectionAttemptDelayMsec "2000";\\nAcquire::ftp::Timeout "30";\\nAcquire::ftp::ConnectionAttemptDelayMsec "2000";\\nAcquire::Retries "15";' > /etc/apt/apt.conf.d/99timeout_and_retries \
     && apt-get update \
     && apt-get -y dist-upgrade \
     && apt-get -y install {apt_packages_str}"""


def generate_add_project_toml_str(config: ProjectConfiguration, real_context_path: str) -> str:
    add_str = "RUN mkdir /app\n"
    add_str += "COPY pyproject.toml poetry.lock* uv.lock* README* /app/\n"
    for package in _remove_duplicates(config.deps_packages):
        if os.path.exists(os.path.join(real_context_path, package)):
            add_str += f"COPY ./{package} /app/{package}\n"
        else:
            print(f"WARNING: {package} not found, skipping it")
    return add_str

def generate_add_packages_str(config: ProjectConfiguration, real_context_path: str) -> str:
    add_str = ""
    for package in _remove_duplicates(config.app_packages):
        if os.path.exists(os.path.join(real_context_path, package)):
            add_str += f"COPY ./{package} /app/{package}\n"
        else:
            print(f"WARNING: {package} not found, skipping it")
    return add_str

def generate_docker_file_content(config: ProjectConfiguration, real_context_path: str) -> str:
    ports_str = "\n".join([f"EXPOSE {port}" for port in config.ports])
    if len(config.entrypoint) > 1:
        cmd_str = "[" + ", ".join(f'"{e}"' for e in config.entrypoint) + "]"
    else:
        cmd_str = f'"{config.entrypoint[0]}"'
    envs_str = "\n".join([f"ENV {key}={value}" for key, value in config.envs.items()])
    labels_str = "\n".join([f"LABEL {key}={value}" for key, value in config.labels.items()])

    if config.package_manager == "poetry":
        pre_apt_commands = f"""RUN pip install poetry=={config.poetry_version}

ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache
"""
        install_cmd = f"""RUN cd /app && poetry install --no-interaction --no-ansi {" ".join(config.build_poetry_install_args)}"""
    else:
        pre_apt_commands = """RUN pip install uv"""
        install_cmd = f"""RUN cd /app && uv sync && uv pip install uv && uv build"""

    return f"""
FROM {config.base_image} AS builder
{pre_apt_commands}

{generate_apt_packages_str(config.build_apt_packages)}
{generate_add_project_toml_str(config, real_context_path)}

{generate_add_packages_str(config, real_context_path)}
{generate_extra_instructions_str(config.extra_build_instructions)}

{install_cmd}

FROM {config.base_image} AS runtime
{generate_apt_packages_str(config.runtime_apt_packages)}
{labels_str}

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
{envs_str}

WORKDIR /app
COPY --from=builder /app/ /app/

{ports_str}
{generate_extra_instructions_str(config.extra_runtime_instructions)}
CMD {cmd_str}"""


def entrypoint() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", help="Project root path", default=os.getcwd())
    parser.add_argument("--generate", help="Generate and persist Dockerfile", action="store_true")
    parser.add_argument("--debug", help="Verbose mode", action="store_true")
    args = parser.parse_args()
    build_image(args.path, verbose=args.debug, generate=args.generate)

def build_image(path: str, verbose: bool = False, generate: bool = False) -> None:
    config = parse_pyproject_toml(path)
    build(config=config, root_path=path, verbose=verbose, generate=generate)


def build(
        root_path: str,
        config: ProjectConfiguration,
        verbose: bool = False,
        generate: bool = False
) -> None:
    """
    Build a docker image from a poetry project.
    """

    with tempfile.NamedTemporaryFile() as tmp:
        dockerfile = tmp.name
        real_context_path = os.path.realpath(root_path)
        content = generate_docker_file_content(config, real_context_path)
        if generate:
            generate_dockerfile_path = os.path.join(real_context_path, "Dockerfile")
            with open(generate_dockerfile_path, "w") as f:
                f.write(content)
            print(f"Stored Dockerfile to {generate_dockerfile_path} 📄")
            return
        tmp.write(content.encode("utf-8"))
        tmp.flush()
        if verbose:
            print("Building with dockerfile content: \n===[Dockerfile]==\n" + content + "\n===[/Dockerfile]==\n")

        dockerignore = os.path.join(real_context_path, ".dockerignore")
        dockerignore_created = write_dockerignore_if_needed(dockerignore)
        try:
            first_tag = config.image_tags[0]
            full_image_name = f"{config.image_name}:{first_tag}"
            print(f"Building image: {full_image_name} 🔨")
            docker_client = docker.from_env()
            start_time = time.time()
            try:
                _, decoder = docker_client.images.build(
                    path=real_context_path,
                    dockerfile=dockerfile,
                    tag=full_image_name,
                    rm=False
                )
                if verbose:
                    print_build_logs(decoder)
            except BuildError as e:
                iterable = iter(e.build_log)
                print("❌ Build failed, printing execution logs:\n\n")
                print_build_logs(iterable)
                print("Error: " + str(e))
                raise e

            for tag in config.image_tags:
                if tag == first_tag:
                    continue
                docker_client.images.get(full_image_name).tag(config.image_name, tag=tag)
            diff = time.time() - start_time
            print(f"Successfully built images: ✅  ({round(diff, 1)}s)")
            for tag in config.image_tags:
                print(f"  - {config.image_name}:{tag}")
        finally:
            if dockerignore_created:
                try:
                    os.remove(dockerignore)
                except:
                    pass


def print_build_logs(iterable):
    while True:
        try:
            item = next(iterable)
            if "stream" in item:
                print(item["stream"], end='')
            elif "error" in item:
                print(item["error"], end='')
            else:
                pass
        except StopIteration:
            break


def write_dockerignore_if_needed(dockerignore: str):
    dockerignore_created = False
    if not os.path.exists(dockerignore):
        print("No .dockerignore found, using a good default one 😉")
        with open(dockerignore, "w") as f:
            f.write("""
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis""")
        dockerignore_created = True
    return dockerignore_created
