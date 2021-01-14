#!/usr/bin/env python
from pathlib import Path
import subprocess

import typer
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


def load_config(path: Path):
    return load(
        subprocess.check_output(
            [
                "ansible-vault",
                "decrypt",
                "--output",
                "-",
                "./group_vars/personalvpn.yml",
            ],
            stderr=subprocess.DEVNULL,
        ).decode(),
        Loader=Loader,
    )["personalvpn"]


app = typer.Typer()


def default_config_path() -> Path:
    return Path("groupvars") / "personal.vpn"


def default_template_path() -> Path:
    return Path("roles") / "personalvpn" / "templates" / "wg0.conf.j2"


@app.command()
def list_peers(config: Path = default_config_path()):
    for peer in load_config(config)["peers"]:
        typer.echo(f"{peer}")


@app.command()
def regenerate_keys(config: Path = default_config_path()):
    pass


@app.command()
def peer_config(
    peer: str,
    config: Path = default_config_path(),
    template: Path = default_template_path(),
):
    pass


@app.command()
def qr_code(
    peer: str,
    config: Path = default_config_path(),
    template: Path = default_template_path(),
):
    pass


if __name__ == "__main__":
    app()
