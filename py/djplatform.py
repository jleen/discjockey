import platform

def prevent_sleep():
    if platform.system() == 'Darwin':
        import pmset
        pmset.prevent_idle_sleep('Disc Jockey Rip')
