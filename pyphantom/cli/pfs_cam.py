#!/usr/bin/env python2
import sys

import click
from pyphantom.flex import Phantom


@click.group()
@click.version_option()
def cli():
    pass


@cli.command()
def info():
    from pyphantom.discover import discover
    from pyphantom.network import get_networks

    networks = get_networks()
    cameras = discover(networks)

    try:
        c = cameras[0]
    except IndexError:
        click.secho("No camera found", fg="red")
        sys.exit()

    with Phantom(c.ip, c.port, c.protocol) as cam:
        cam.connect()
        cam_info = cam.structures.info
        click.secho('Connected to a {} at {}'.format(cam_info.model, c.ip), fg='green')
        for key in dir(cam_info):
            click.echo(key + ': ', nl=False)
            click.secho(str(getattr(cam_info, key)), bold=False, fg='yellow')


if __name__ == "__main__":
    cli()
