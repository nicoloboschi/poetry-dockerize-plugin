import os

from cleo.commands.command import Command
from cleo.helpers import option
from poetry.plugins.application_plugin import ApplicationPlugin

from poetry_dockerize_plugin.builder import build_image


class DockerCommand(Command):

    name = "dockerize"
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
            description="Debug mode",
        ),
    ]

    def handle(self) -> int:
        build_image(
            path=self.option("path"),
            verbose=self.option("debug"),
        )
        return 0


def factory():
    return DockerCommand()


class DockerApplicationPlugin(ApplicationPlugin):
    def activate(self, application):
        application.command_loader.register_factory("dockerize", factory)