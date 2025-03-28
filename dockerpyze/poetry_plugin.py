import os

from cleo.commands.command import Command
from cleo.helpers import option
from poetry.plugins.application_plugin import ApplicationPlugin

from dockerize.builder import build_image


class DockerCommand(Command):

    name = "dockerpyze"
    description = "Generate a docker image of your project automatically, without configuration."
    options = [  # noqa: RUF012
        option(
            "path",
            "Project root path",
            flag=False,
            default=os.getcwd(),
        ),
        option(
            "debug",
            flag=True,
            description="(dockerpyze) Debug mode",
        ),
        option(
            "generate",
            description="(dockerpyze) Generate and persist Dockerfile",
            flag=True,
        ),
    ]

    def handle(self) -> int:
        build_image(
            path=self.option("path"),
            verbose=self.option("debug"),
            generate=self.option("generate"),
        )
        return 0


def factory():
    return DockerCommand()


class DockerApplicationPlugin(ApplicationPlugin):
    def activate(self, application):
        application.command_loader.register_factory("dockerpyze", factory)