from distutils.core import setup
from glob import glob
import os

libdir = 'share/obkey/icons'
localedir = 'share/locale'

langs = [a[len("locale/"):] for a in glob('locale/*')]
locales = [(os.path.join(localedir, l, 'LC_MESSAGES'),
            [os.path.join('locale', l, 'LC_MESSAGES', 'obkey.mo')]) for l in langs]

setup(name='obkey',
      version='1.0',
      description='Openbox Key Editor',
      author='nsf',
      author_email='no.smile.face@gmail.com',
      scripts=['obkey'],
      py_modules=['obkey_classes'],
      data_files=[(libdir, ['icons/add_child.png', 'icons/add_sibling.png'])] + locales
      )
