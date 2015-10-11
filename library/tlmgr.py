#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright © 2015 Fabian Köhler <fkoehler1024@googlemail.com>

import os.path
import re


def update_self(module, tlmgr_path, dry_run=False):
    cmd = tlmgr_path+" update --self"
    if dry_run:
        cmd += " --list"
    rc, stdout, stderr = module.run_command(cmd)
    if rc == 0:
        return stdout.find("tlmgr: no updates for tlmgr present") < 0
    else:
        module.fail_json(msg="could not update tlmgr itself")


def update_all(module, tlmgr_path, dry_run=False):
    cmd = tlmgr_path+" update --all"
    if dry_run:
        cmd += " --list"
    rc, stdout, stderr = module.run_command(cmd)
    if rc == 0:
        return stdout.find("tlmgr: no updates available") < 0
    else:
        module.fail_json(msg="could not update packages (all)")


def is_installed(module, tlmgr_path, package):
    cmd = tlmgr_path+" info "+package
    rc, stdout, stderr = module.run_command(cmd)
    if rc != 0:
        module.fail_json(msg="cannot query status of package" % package)
    if stdout.find("tlmgr: cannot find package") >= 0:
        module.fail_json(
            msg="cannot find package %s" % package
        )

    m = re.search(r"installed\:\s+(?P<state>Yes|No)", stdout)
    if not m:
        module.fail_json(
            msg="cannot extract status of package %s" % package
        )

    return m.groupdict()["state"] == "Yes"


def install_packages(module, tlmgr_path, pkgs):
    base_cmd = tlmgr_path+" install "
    changed = 0
    for pkg in pkgs:
        if is_installed(module, tlmgr_path, pkg):
            continue
        rc, stdout, stderr = module.run_command(base_cmd+pkg)
        if rc != 0:
            module.fail_json(
                msg="cannot install package %s" % pkg
            )
        changed += 1
    module.exit_json(
        changed=(changed > 0),
        msg="installed %s packages" % changed
    )


def remove_packages(module, tlmgr_path, pkgs):
    base_cmd = tlmgr_path+" remove "
    changed = 0
    for pkg in pkgs:
        if not is_installed(module, tlmgr_path, pkg):
            continue
        rc, stdout, stderr = module.run_command(base_cmd+pkg)
        if rc != 0:
            module.fail_json(
                msg="cannot remove package %s" % pkg
            )
        changed += 1
    module.exit_json(
        changed=(changed > 0),
        msg="removed %s packages" % changed
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(aliases=["pkg"]),
            state=dict(choices=["installed", "absent"]),
            update_self=dict(default="no", choices=BOOLEANS, type="bool"),
            update_all=dict(default="no", choices=BOOLEANS, type="bool"),
        ),
        required_one_of=[["name", "update_self", "update_all", "available"]],
        supports_check_mode=True
    )
    tlmgr_path = module.get_bin_path("tlmgr", True)

    if not os.path.exists(tlmgr_path):
        module.fail_json(
            msg="cannot find tlmgr in path %s" % tlmgr_path
        )

    p = module.params

    if p["update_self"]:
        changed = update_self(module, tlmgr_path, module.check_mode)
        if not p["name"]:
            module.exit_json(changed=changed, msg="updated tlmgr")

    if p["update_all"]:
        changed = update_all(module, tlmgr_path, module.check_mode)
        if not p["name"]:
            module.exit_json(changed=changed, msg="updated TeX Live packages")

    if p["name"]:
        if isinstance(p["name"], str):
            pkgs = p["name"].split(",")
        else:
            pkgs = p["name"]

        with open("/home/fabian/ansible.tmp", "w") as f:
            f.write(", ".join(pkgs)+"\n\n")

        if p["state"] == "installed":
            install_packages(module, tlmgr_path, pkgs)
        elif p["state"] == "absent":
            remove_packages(module, tlmgr_path, pkgs)


from ansible.module_utils.basic import *
if __name__ == '__main__':
        main()
