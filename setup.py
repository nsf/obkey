from distutils.core import setup
from distutils.sysconfig import get_config_var
import sys

libdir = 'share/obkey'
print get_config_var('prefix')
sys.exit(1)


setup(name='obkey',
      version='0.9',
      description='Openbox Key Editor',
      author='nsf',
      author_email='no.smile.face@gmail.com',
      scripts=['obkey'],
      py_modules=['obkey_classes'],
      data_files=[(libdir, ['icons/add_child.png', 'icons/add_sibling.png'])]
      )
