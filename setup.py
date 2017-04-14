from setuptools import setup

setup(name='hyphe-traph',
      version='0.0.1',
      description='A Trie/Graph hybrid memory structure used by the Hyphe crawler to index pages & webentities.',
      url='http://github.com/medialab/hyphe-traph',
      license='MIT',
      packages=['traph'],
      install_requires=[
        'numpy'
      ]
      zip_safe=False)
