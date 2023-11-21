from cleo.commands.command import Command
from cleo.helpers import option
from poetry.plugins.application_plugin import ApplicationPlugin
import docker
import tempfile

from poetry_auto_docker_plugin.builder import build


class DockerCommand(Command):

    name = "auto-docker"
    description = "Generate a docker image of your project automatically."
    options = [  # noqa: RUF012
        option(
            "docker-file",
            "f",
            "Docker file path",
            flag=False,
            default="",
        ),
        option(
            "entrypoint-module",
            "Module to run as entrypoint",
            flag=False,
            default=""
        )
    ]

    def handle(self) -> int:
        self.line("Docker build...")
        build(
            entrypoint_module=self.option("entrypoint-module"),
            dockerfile=self.option("docker-file"),
            image_tag="latest"
        )
        self.line("Image built!")
        return 0


def factory():
    return DockerCommand()


class DockerApplicationPlugin(ApplicationPlugin):
    def activate(self, application):
        application.command_loader.register_factory("auto-docker", factory)