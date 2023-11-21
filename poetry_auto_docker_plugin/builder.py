import os.path
import tempfile

import docker


def build(
    entrypoint_module = "",
    entrypoint_script = "",
    entrypoint_override = "",
    python_version = "3.11",
    ports = [],
    dockerfile = "",
    image_name = "",
    image_tag = "latest",
    context_path = ".",
) -> None:
    """
    Build a docker image from a poetry project.
    """
    docker_client = docker.from_env()
    cmd_str = ""

    if entrypoint_script:
        cmd_str = f"[{entrypoint_script}]"
    elif entrypoint_module:
        cmd_str = f"[\"python\", \"-m\", \"{entrypoint_module}\"]"
    elif entrypoint_override:
        # todo implemnet
        pass

    with tempfile.NamedTemporaryFile() as tmp:

        if not dockerfile:
            dockerfile = tmp.name

            ports_str = ""
            for port in ports:
                ports_str += f"EXPOSE {port}\n"

            content = f"""
                    FROM python:{python_version}-slim-buster as builder
                    RUN apt-get update && apt-get install -y git
 
                    RUN pip install poetry==1.4.2
                     
                    ENV POETRY_NO_INTERACTION=1
                    ENV POETRY_VIRTUALENVS_IN_PROJECT=1
                    ENV POETRY_VIRTUALENVS_CREATE=1
                    ENV POETRY_CACHE_DIR=/tmp/poetry_cache
                    
                    
                    ADD . /app/
                    
                    RUN cd /app && poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

                    FROM python:{python_version}-slim-buster as runtime
                    
                    ENV PATH="/app/.venv/bin:$PATH"

                    WORKDIR /app
                    COPY --from=builder /app/ /app/
 
                    {ports_str}                
                    CMD {cmd_str}
                    """
            print(content)
            tmp.write(content.encode("utf-8"))
            tmp.flush()
        real_context_path = os.path.realpath(context_path)
        print("Build context path: " + real_context_path)
        if not image_name:
            image_name = os.path.basename(real_context_path)
        full_image_name = f"{image_name}:{image_tag}"

        print("Building image: " + full_image_name)
        docker_client.images.build(
            path=real_context_path,
            dockerfile=dockerfile,
            tag=full_image_name
        )
