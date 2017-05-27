from setuptools import setup

setup(
    name='discjockey',
    version='0.1',
    packages=['discjockey'],
    entry_points={
        'console_scripts': ['dj = discjockey.transcode:transcode',
                            'frip = discjockey.rip:rip',
                            'frename = discjockey.rip:rename',
                            'fident = discjockey.ident:ident',
                            'fit = discjockey.fit:fit',
                            'cosmetize = discjockey.beautify:cosmetize',
                            'sleepless = discjockey.sleepless:sleepless']
    }
)
