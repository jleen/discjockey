from setuptools import setup

setup(
    name='discjockey',
    version='0.1',
    packages=['discjockey'],
    entry_points={
        'console_scripts': ['cosmetize = discjockey.beautify:cosmetize',
                            'decamp = discjockey.decamp:decamp',
                            'dj = discjockey.transcode:transcode',
                            'fident = discjockey.ident:ident',
                            'fit = discjockey.fit:fit',
                            'frename = discjockey.rip:rename',
                            'frip = discjockey.rip:rip',
                            'largo = discjockey.largo:largo',
                            'sleepless = discjockey.sleepless:sleepless']
    }
)
