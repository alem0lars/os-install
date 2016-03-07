# ------------------------------------------------------------------------------
# chrooted ---------------------------------------------------------------------

def chrooted(command, path, profile='/etc/profile', work_dir=None):
    prefix = "chroot {path} bash -c 'source {profile}; ".format(
        path=path, profile=profile)
    if work_dir:
        prefix += 'cd {work_dir}; '.format(work_dir=work_dir)
    prefix += command
    prefix += "'"
    return prefix

# ------------------------------------------------------------------------------
# vim: set filetype=python :
