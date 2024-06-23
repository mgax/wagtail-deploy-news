from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from opslib import LocalHost, Stack as BaseStack, evaluate
from opslib.cli import ComponentGroup
from opslib.components import TypedComponent
from opslib.local import Call
from opslib_contrib.fly import Fly
from opslib_contrib.localsecret import LocalSecret


# Configuration for the FlyApp component. Will show up as `self.props` in the
# component instance.
@dataclass
class FlyAppProps:
    name: str
    region: str
    volume_size: int = 1


class FlyApp(TypedComponent(FlyAppProps)):
    def build(self):
        # Set up a helper component, `self.base_dir`, that can run commands
        # locally from the project root. It will run `flyctl` for us.
        self.localhost = LocalHost()
        self.base_dir = self.localhost.directory(path=settings.BASE_DIR)

        # Set up the Terraform provider.
        self.fly = Fly()

        # Create a Fly app with a volume.
        self.app = self.fly.app(
            name=self.props.name,
        )
        self.volume = self.app.volume(
            name="wagtail",
            region=self.props.region,
            size=self.props.volume_size,
        )

        # Generate a secret key and store it in opslib's state directory.
        self.secret_key = LocalSecret()

        # Set the secret key on the fly app. This only runs when the value of
        # `self.secret_key` changes.
        self.set_secret_key = Call(
            func=lambda: self.flyctl(
                *["secrets", "set", f"SECRET_KEY={evaluate(self.secret_key.value)}"],
                capture_output=False,
            ),
            run_after=[self.secret_key],
        )

        # Call `flyctl deploy` to deploy the app. This runs every time we
        # deploy a `FlyApp` opslib component (either staging or production).
        self.fly_deploy = Call(
            func=lambda: self.flyctl("deploy", capture_output=False),
        )

    # Helper function that runs `flyctl --app={app_name}` in the root of our
    # project.
    def flyctl(self, *args, **kwargs):
        return self.base_dir.run(
            "flyctl", f"--app={self.app.props.name}", *args, **kwargs
        )

    def add_commands(self, cli: ComponentGroup):
        # In case we want to run `flyctl` for one of our environments, e.g.
        # `./manage.py opslib staging flyctl ...`.
        @cli.forward_command
        def flyctl(args):
            self.flyctl(*args, capture_output=False, exit_on_error=True)

        # Load initial data: `./manage.py opslib staging load-initial-data`
        @cli.command
        def load_initial_data():
            load_cmd = "./manage.py load_initial_data"
            fly_cmd = ["ssh", "console", "-u", "wagtail", "-C", load_cmd]
            self.flyctl(*fly_cmd, capture_output=False, exit_on_error=True)


# The opslib stack, i.e. the top-level component of opslib's world.
class Stack(BaseStack):
    def build(self):
        # An instance of the FlyApp component, for staging.
        self.staging = FlyApp(
            name="mgax-news-staging",
            region="otp",
        )

        # An instance of the FlyApp component, for production.
        self.production = FlyApp(
            name="mgax-news-production",
            region="otp",
            volume_size=10,
        )


stack = Stack(
    # opslib needs a place to store state.
    stateroot=Path(settings.BASE_DIR) / ".opslib",
)
