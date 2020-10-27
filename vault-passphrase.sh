#!/bin/sh
set -euf -o pipefail
gpg --decrypt vault-passphrase.pgp
