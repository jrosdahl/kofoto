import sys

if sys.platform[:3] != "win":
    sys.exit()

if sys.argv[1] == "-install":
    import distutils.sysconfig
    import os
    import shutil

    target = os.path.join(
        distutils.sysconfig.PREFIX,
        "Scripts",
        "gkofoto-start.pyw")

    try:
        programs_dir = get_special_folder_path("CSIDL_COMMON_PROGRAMS")
    except OSError:
        try:
            programs_dir = get_special_folder_path("CSIDL_PROGRAMS")
        except OSError, reason:
            print "Couldn't install shortcuts: %s" % reason
            sys.exit()
    programs_shortcut = os.path.join(programs_dir, "Kofoto.lnk")
    create_shortcut(target, "Kofoto", programs_shortcut)
    file_created(programs_shortcut)

    try:
        desktop_dir = get_special_folder_path("CSIDL_COMMON_DESKTOPDIRECTORY")
    except OSError:
        try:
            desktop_dir = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
        except OSError, reason:
            print "Couldn't install shortcuts: %s" % reason
            sys.exit()
    desktop_shortcut = os.path.join(desktop_dir, "Kofoto.lnk")
    create_shortcut(target, "Kofoto", desktop_shortcut)
    file_created(desktop_shortcut)

    print "Created Kofoto shortcut on the Desktop and in the Start menu."
