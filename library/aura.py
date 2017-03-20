#!/usr/bin/python
# -*- coding: utf-8 -*-
from ansible.module_utils.basic import *

ANSIBLE_METADATA = {"status": ["preview"],
                    "supported_by": "community",
                    "version": "0.1"}


def extract_version(aura_output):
    lines = aura_output.splitlines()
    for line in lines:
        if "Version" in line:
            return line.split(":")[1].strip()
    return None


def query_package(module, aura_path, name, state="present"):
    cmd = "%s -Qi %s" % (aura_path, name)
    rc, stdout, stderr = module.run_command(cmd, check_rc=False)
    if rc != 0:
        # package is not present locally
        return False, False, False

    local_version = extract_version(stdout)

    cmd = "%s -Ai %s" % (aura_path, name)
    rc, stdout, stderr = module.run_command(cmd, check_rc=False)
    remote_version = extract_version(stdout)

    if rc == 0:
        return True, (local_version == remote_version), False

    return True, True, True


def check_packages(module, aura_path, packages, state):
    would_be_changed = []
    for pkg in packages:
        installed, up_to_date, _ = query_package(module, aura_path, pkg)

        if state in ["present", "latest"] and not installed:
            # package would be installed
            would_be_changed.append(pkg)
            continue

        if state == "absent" and installed:
            # package would be removed
            would_be_changed.append(pkg)
            continue

        if state == "latest" and not up_to_date:
            # package would be removed
            would_be_changed.append(pkg)
            continue

    if would_be_changed:
        if state == "absent":
            state = "removed"
        module.exit_json(changed=True, msg="%s package(s) would be %s" % (
            len(would_be_changed), state)
        )
    else:
        module.exit_json(changed=False, msg="package(s) already %s" % state)


def install_packages(module, aura_path, packages, state):
    install_count = 0
    user = module.params["user"]
    errored_packages = []
    message = ""

    for pkg in packages:
        installed, up_to_date, latest_error = query_package(module, aura_path, pkg)

        if latest_error and state == "latest":
            errored_packages.append(pkg)

        if installed and (state == "present" or (state == "latest" and up_to_date)):
            continue

        cmd = "%s -A --noconfirm --builduser=%s %s" % (aura_path, user, pkg)
        rc, stdout, stderr = module.run_command(cmd, check_rc=False)

        if rc != 0:
            module.fail_json(msg="failed to install %s: %s" % (pkg, stderr))

        install_count += 1

    if state == "latest" and len(errored_packages):
        message = " But could not ensure 'latest' state for %s package(s) as remote version could not be fetched." % (package_err)

    if install_count > 0:
        module.exit_json(changed=True, msg="installed %s package(s).%s" % (install_count, message))

    module.exit_json(changed=False, msg="package(s) already installed.%s" % (message))


def remove_packages(module, aura_path, pkgs):
    if module.params["force"]:
        args = "Rdd"
    else:
        args = "R"

    remove_count = 0
    for pkg in pkgs:
        installed, up_to_date, _ = query_package(pkg)
        if not installed:
            continue

        cmd = "%s -%s %s --noconfirm" % (aura_path, args, pkg)
        rc, stdout, stderr = module.run_command(cmd, check_rc="False")

        if rc != 0:
            module.fail_json(msg="failed to remove %s" % (pkg))

        remove_count += 1

    if remove_count > 0:
        module.exit_json(changed=True, msg="removed %s package(s)" % remove_count)

    module.exit_json(changed=False, msg="package(s) already absent" % remove_count)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(aliases=["pkg", "packages"], type="list"),
            state=dict(default="present", choices=["present", "latest", "absent"]),
            force=dict(default=False, type="bool"),
            user=dict(default="ansible")
        ),
        required_one_of=[["name"]],
        supports_check_mode=True
    )

    aura_path = module.get_bin_path("aura", True)
    if not os.path.exists(aura_path) or not os.path.isfile(aura_path):
        module.fail_json(msg="cannot find aura in path %s" % (aura_path))

    p = module.params

    pkgs = p["name"]
    state = p["state"]
    if module.check_mode:
        check_packages(module, aura_path, pkgs, state)

    if state == "absent":
        remove_packages(module, aura_path, pkgs)
    else:
        install_packages(module, aura_path, pkgs, state)


if __name__ == '__main__':
    main()
