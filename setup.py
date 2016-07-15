from setuptools import setup

setup(
    name = 'discjockey',
    version = '0.1',
    packages = [ 'discjockey' ],
    entry_points = {
        'console_scripts': [ 'frip = discjockey.djrip:rip',
                             'fident = discjockey.djident:ident',
                             'fit = discjockey.djfit:fit',
                             'cosmetize = discjockey.djbeautify:cosmetize' ]
    },
)
