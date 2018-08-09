from setuptools import setup

setup(name='pyphantom',
      description='Phantom highspeed camera control',
      url='http://gitlab.com/kamerawerk/pyphantom',
      author='Ben Hagen',
      author_email='ben@kamerawerk.ch',
      install_requires=['psutil', 'PyYAML', 'netifaces', 'cached_property'],
      packages=['pyphantom'],
      scripts=[],
      use_scm_version=True,
      setup_requires=['pytest-runner', 'setuptools_scm'],
      tests_require=['pytest', 'tempdir'],
      )
