#!/usr/bin/python
# Copyright © 2015 Fabian Köhler <fkoehler1024@googlemail.com>

import os.path


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


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(aliases=["pkg"]),
            state=dict(choices=["installed", "absent"]),
            update_self=dict(default="no", choices=BOOLEANS, type="bool"),
            update_all=dict(default="no", choices=BOOLEANS, type="bool"),
        ),
        required_one_of=[["name", "update_self", "update_all"]],
        supports_check_mode=True
    )
    tlmgr_path = module.get_bin_path("tlmgr", True)

    if not os.path.exists(tlmgr_path):
        module.fail_json(msg="cannot find tlmgr in path {}".format(tlmgr_path))

    p = module.params

    if p["update_self"]:
        changed = update_self(module, tlmgr_path, module.check_mode)
        if not p["name"]:
            module.exit_json(changed=changed, msg="updated tlmgr")

    if p["update_all"]:
        changed = update_all(module, tlmgr_path, module.check_mode)
        if not p["name"]:
            module.exit_json(changed=changed, msg="updated TeX Live packages")


from ansible.module_utils.basic import *
if __name__ == '__main__':
        main()
