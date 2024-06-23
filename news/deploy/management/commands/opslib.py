import argparse
from django.core.management.base import BaseCommand, CommandParser
from opslib.cli import get_main_cli

from ...stack import stack


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser):
        parser.add_argument("opslib_args", nargs=argparse.REMAINDER)

    def handle(self, **options):
        # Invoke opslib using its own built-in CLI
        cli = get_main_cli(lambda: stack)
        cli(args=options["opslib_args"], obj={})
