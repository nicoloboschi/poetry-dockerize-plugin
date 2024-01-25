import os

from poetry_dockerize_plugin.builder import build_image, parse_pyproject_toml, generate_docker_file_content

dirname = os.path.dirname(__file__)
test_project = os.path.join(dirname, 'test_project')
def test() -> None:
#    build_image(path=test_project)
    build_image(path="/Users/nicoloboschi/dev/ragstack-ai")


def test_parse() -> None:
    config = parse_pyproject_toml(test_project)
    content = generate_docker_file_content(config)
    print(content)
    assert content == """
FROM python:3.11-slim-buster as builder
RUN pip install poetry==1.4.2

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

ADD . /app/

RUN cd /app && poetry install && rm -rf $POETRY_CACHE_DIR

FROM python:3.11-slim-buster as runtime

LABEL org.opencontainers.image.title=poetry-sample-app
LABEL org.opencontainers.image.version=0.1.0
LABEL org.opencontainers.image.authors=['Nicolò Boschi <boschi1997@gmail.com>']
LABEL org.opencontainers.image.licenses=
LABEL org.opencontainers.image.url=
LABEL org.opencontainers.image.source=

ENV PATH="/app/.venv/bin:$PATH"
ENV PORT=5001

WORKDIR /app
COPY --from=builder /app/ /app/

EXPOSE 5001
                
CMD python -m app"""
