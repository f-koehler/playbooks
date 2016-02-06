def query_package(module, aura_path, name, state="present"):
    if state == "present":
        cmd = "%s -Ai %s" % (aura_path, name)
        rc, out, err = module.run_command(cmd, check_rc=False)
        if rc != 0:
            return False, False, False
