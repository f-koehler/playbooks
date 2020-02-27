#!/usr/bin/python
# -*- coding: utf-8 -*-
from ansible.module_utils.basic import AnsibleModule
import re

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community"
}

DOCUMENTATION = """
"""

EXAMPLES = """
"""

RETURN = """
packages:
    description: A list of packages that have been changed
    type: list
"""

re_upgrade = re.compile(r'([\w-]+) ((?:\S+)-(?:\S+)) -> ((?:\S+)-(?:\S+))')
re_package_file = re.compile(r".*\.pkg\.tar(\.(gz|bz2|xz|lrz|lzo|Z))?$")
re_package_file_sub = re.compile(r'-[0-9].*$')
re_version = re.compile(r"^Version\s+:\s+(.+)$", re.MULTILINE)


def query_package(module, aura_path, name, state="present"):
    if state == "present":
        # query local package information
        cmd = "{} -Qi {}".format(aura_path, name)
        ret, stdout, stderr = module.run_command(cmd, check_rc=False)
        if ret != 0:
            # package is not installed locally
            return False, False, False
        local_version = re_version.search(stdout).group(1)

        # query remote package information
        cmd = "{} -Ai {}".format(aura_path, name)
        ret, stdout, stderr = module.run_command(cmd, check_rc=False)
        remote_version = re_version.search(stdout).group(1)
        if ret == 0:
            return True, (local_version == remote_version), False

        # last True denotes unknown package
        return True, True, True


def upgrade(module, aura_path):
    cmd_need_upgrade = "{} -Qu".format(aura_path)
    cmd_upgrade = "{} -Suq --noconfirm".format(aura_path)

    ret, stdout, stderr = module.run_command(cmd_need_upgrade, check_rc=False)
    data = stdout.split("\n")
    data.remove("")

    packages = []
    diff = {
        "before": "",
        "after": "",
    }

    if ret == 0:
        for entry in data:
            m = re_upgrade.search(entry)
            packages.append(m.group(1))
            diff["before"] += "{}-{}\n".format(m.group(1), m.group(2))
            diff["after"] += "{}-{}\n".format(m.group(3), m.group(4))

        if module.check_mode:
            module.exit_json(
                changed=True,
                msg="{} package(s) would be upgraded".format(len(data)),
                packages=packages,
                diff=diff)

        ret, stdout, stderr = module.run_command(cmd_upgrade, check_rc=False)
        if ret == 0:
            module.exit_json(
                changed=True,
                msg="{} package(s) upgraded",
                packages=packages,
                diff=diff)
        else:
            module.fail_json(msg="Could not upgrade")
    else:
        # no upgrade required
        module.exit_json(
            changed=False, msg="No upgrade required", packages=packages)


def expand_groups(module, aura_path, pkgs):
    expanded = []
    for pkg in pkgs:
        if pkg:
            cmd = "{} -Sgq {}".format(aura_path, pkg)
            ret, stdout, stderr = module.run_command(cmd, check_rc=False)

            if ret == 0:
                # pkg is a package group
                for name in stdout.split("\n"):
                    name = name.strip()
                    if name:
                        expanded.append(name)
            else:
                expanded.append(pkg)

    return expanded


def check_packages(module, aura_path, packages, state):
    would_be_changed = []
    diff = {"before": "", "after": "", "before_header": "", "after_header": ""}

    for package in packages:
        installed, updated, unknown = query_package(module, aura_path, package)
        if ((state in ["present", "latest"] and not installed)
                or (state == "absent" and installed)
                or (state == "latest" and not updated)):
            would_be_changed.append(package)

    if would_be_changed:
        if state == "absent":
            state = "removed"

        if module._diff and (state == "removed"):
            diff["before_header"] = "removed"
            diff["before"] = "\n".join(would_be_changed) + "\n"
        elif module._diff and ((state == "present") or (state == "latest")):
            diff["after_header"] = "installed"
            diff["after"] = "\n".join(would_be_changed) + "\n"

        module.exit_json(
            changed=True,
            msg="{} package(s) would be %s".format(
                len(would_be_changed), state),
            diff=diff)
    else:
        module.exit_json(
            changed=False,
            msg="package(s) already %s".format(state),
            diff=diff)


def remove_packages(module, aura_path, packages):
    data = []
    diff = {
        'before': '',
        'after': '',
    }

    if module.params["recurse"] or module.params["force"]:
        if module.params["recurse"]:
            args = "Rs"
        if module.params["force"]:
            args = "Rdd"
        if module.params["recurse"] and module.params["force"]:
            args = "Rdds"
    else:
        args = "R"

    remove_c = 0
    # Using a for loop in case of error, we can report the package that failed
    for package in packages:
        # Query the package first, to see if we even need to remove
        installed, updated, unknown = query_package(module, aura_path,
                                                    package)
        if not installed:
            continue

        cmd = "%s -%s %s --noconfirm --noprogressbar" % (aura_path, args,
                                                         package)
        rc, stdout, stderr = module.run_command(cmd, check_rc=False)

        if rc != 0:
            module.fail_json(msg="failed to remove %s" % (package))

        if module._diff:
            d = stdout.split('\n')[2].split(' ')[2:]
            for i, pkg in enumerate(d):
                d[i] = re.sub('-[0-9].*$', '', d[i].split('/')[-1])
                diff['before'] += "%s\n" % pkg
            data.append('\n'.join(d))

        remove_c += 1

    if remove_c > 0:
        module.exit_json(
            changed=True, msg="removed %s package(s)" % remove_c, diff=diff)

    module.exit_json(changed=False, msg="package(s) already absent")


def install_packages(module, aura_path, state, packages, package_files):
    install_c = 0
    package_err = []
    message = ""
    data = []
    diff = {
        'before': '',
        'after': '',
    }

    to_install_repos = []
    to_install_files = []
    for i, package in enumerate(packages):
        # if the package is installed and state == present or state == latest and is up-to-date then skip
        installed, updated, latestError = query_package(
            module, aura_path, package)
        if latestError and state == 'latest':
            package_err.append(package)

        if installed and (state == 'present' or
                          (state == 'latest' and updated)):
            continue

        if package_files[i]:
            to_install_files.append(package_files[i])
        else:
            to_install_repos.append(package)

    if to_install_repos:
        cmd = "%s -S %s --noconfirm --noprogressbar --needed" % (
            aura_path, " ".join(to_install_repos))
        rc, stdout, stderr = module.run_command(cmd, check_rc=False)

        if rc != 0:
            module.fail_json(msg="failed to install %s: %s" %
                             (" ".join(to_install_repos), stderr))

        data = stdout.split('\n')[3].split(' ')[2:]
        data = [i for i in data if i != '']
        for i, pkg in enumerate(data):
            data[i] = re.sub('-[0-9].*$', '', data[i].split('/')[-1])
            if module._diff:
                diff['after'] += "%s\n" % pkg

        install_c += len(to_install_repos)

    if to_install_files:
        cmd = "%s -U %s --noconfirm --noprogressbar --needed" % (
            aura_path, " ".join(to_install_files))
        rc, stdout, stderr = module.run_command(cmd, check_rc=False)

        if rc != 0:
            module.fail_json(msg="failed to install %s: %s" %
                             (" ".join(to_install_files), stderr))

        data = stdout.split('\n')[3].split(' ')[2:]
        data = [i for i in data if i != '']
        for i, pkg in enumerate(data):
            data[i] = re.sub('-[0-9].*$', '', data[i].split('/')[-1])
            if module._diff:
                diff['after'] += "%s\n" % pkg

        install_c += len(to_install_files)

    if state == 'latest' and len(package_err) > 0:
        message = "But could not ensure 'latest' state for %s package(s) as remote version could not be fetched." % (
            package_err)

    if install_c > 0:
        module.exit_json(
            changed=True,
            msg="installed %s package(s). %s" % (install_c, message),
            diff=diff)

    module.exit_json(
        changed=False,
        msg="package(s) already installed. %s" % (message),
        diff=diff)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="list", aliases=["package", "pkg"]),
            state=dict(
                type="str",
                default="present",
                choices=[
                    "absent", "installed", "latest", "present", "removed"
                ]),
            recurse=dict(type="bool", default=False),
            force=dict(type="bool", default=False),
            upgrade=dict(type="bool", default=False),
        ),
        required_one_of=[["name", "upgrade"]],
        supports_check_mode=True,
    )

    aura_path = module.get_bin_path("aura", True)
    parameters = module.params

    if parameters["state"] in ["present", "installed"]:
        parameters["state"] = "present"
    elif parameters["state"] in ["absent", "removed"]:
        parameters["state"] = "absent"

    if parameters["upgrade"]:
        upgrade(module, aura_path)

    if parameters["name"]:
        pkgs = expand_groups(module, aura_path, parameters["name"])

        pkg_files = []
        for i, pkg in enumerate(pkgs):
            if re_package_file.match(pkg):
                pkg_files.append(pkg)
                pkgs[i] = re_package_file_sub.sub("", pkgs[i].split("/")[-1])
            else:
                pkg_files.append(None)

        if module.check_mode:
            check_packages(module, aura_path, pkgs, parameters["state"])

        if parameters["state"] in ["present", "latest"]:
            install_packages(module, aura_path, parameters["state"], pkgs,
                             pkg_files)
        else:
            remove_packages(module, aura_path, pkgs)


if __name__ == "__main__":
    main()
