#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

# requirements
install_requires = [
    "six>=1.10.0",
    "Django>=1.7.4",
    "requests>=2.18.1",
    "redis>=2.10.5",
]

dependency_links = [
      'git+ssh://git@git.gengmei.cc/backend/helios.git@v0.4.5#egg=helios==0.4.5',
      'git+ssh://git@git.gengmei.cc/backend/gm-logging.git@v0.6.0b3#egg=gm-logging==0.6.0b3',
      'git+ssh://git@git.gengmei.cc/backend/gm-types.git@master',
]

setup(name="gm-share-tool",
      version=__import__("gm_share").__version__,
      description="gengmei share and weixin tool",
      author="jesse",
      author_email="yanjiayi@gmei.com",
      packages=find_packages(),
      url="https://github.com/JesseYan/gm-share-tool",
      install_requires=install_requires,
      dependency_links=dependency_links)
