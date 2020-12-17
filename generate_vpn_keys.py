#!/usr/bin/python
import subprocess
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


all_config = load(
    subprocess.check_output(
        ["ansible-vault", "decrypt", "--output", "-", "./group_vars/personalvpn.yml"]
    ).decode(),
    Loader=Loader,
)
config = all_config["personalvpn"]

# generate private keys
for peer in config["peers"]:
    config["private"] = config.get("private", {})
    if (peer in config["private"]) and config["private"]:
        continue
    config["private"][peer] = subprocess.check_output(["wg", "genkey"]).decode().strip()

# generate public keys
for peer in config["peers"]:
    config["public"] = config.get("public", {})
    if (peer in config["public"]) and config["public"]:
        continue
    config["public"][peer] = (
        subprocess.check_output(
            ["wg", "pubkey"], input=config["private"][peer].encode()
        )
        .decode()
        .strip()
    )

# generate PSKs
config["psk"] = config.get("psk", {})
peers = list(config["peers"].keys())
for (i, peer_A) in enumerate(peers):
    config["psk"][peer_A] = config["psk"].get(peer_A, {})
    for peer_B in peers[:i]:
        config["psk"][peer_B] = config["psk"].get(peer_B, {})

        config["psk"][peer_A][peer_B] = config["psk"][peer_A].get("peer_B", "")
        config["psk"][peer_B][peer_A] = config["psk"][peer_B].get("peer_A", "")

        if config["psk"][peer_A][peer_B] and config["psk"][peer_B][peer_A]:
            if config["psk"][peer_A][peer_B] == config["psk"][peer_B][peer_A]:
                continue

        psk = subprocess.check_output(["wg", "genpsk"]).decode().strip()
        config["psk"][peer_A][peer_B] = psk
        config["psk"][peer_B][peer_A] = psk

all_config["personalvpn"] = config

subprocess.check_output(
    ["ansible-vault", "encrypt", "--output", "./group_vars/personalvpn.yml"],
    input=dump(all_config, Dumper=Dumper).encode(),
)
