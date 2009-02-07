#!/usr/bin/python
#-----------------------------------------------------------------------
# Openbox Key Editor
# Copyright (C) 2009 nsf
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------------

import sys, os
import gtk
import gobject
import obkey_classes
import xml.dom.minidom

def die(widget, data=None):
	gtk.main_quit()

# get rc file
path = os.getenv("HOME") + "/.config/openbox/rc.xml"
if len(sys.argv) == 2:
	path = sys.argv[1]

#!!!!!!!!!!!!!!!! DEVELOPMENT VERSION !!!!!!!!!!!!!!!!!!!!!!
if not os.path.exists(path+".bak"):
	os.system("cp {0} {0}.bak".format(path))
#-----------------------------------------------------------

ob = obkey_classes.OpenboxConfig()
ob.load(path)

win = gtk.Window(gtk.WINDOW_TOPLEVEL)
win.set_default_size(640,480)
win.connect("destroy", die)

tbl = obkey_classes.PropertyTable()
al = obkey_classes.ActionList(tbl)
ktbl = obkey_classes.KeyTable(al, ob)

vbox = gtk.VPaned()
vbox.pack1(tbl.widget, True, False)
vbox.pack2(al.widget, True, False)

hbox = gtk.HPaned()
hbox.pack1(ktbl.widget, True, False)
hbox.pack2(vbox, False, False)

win.add(hbox)
win.show_all()
# get rid of stupid autocalculation
w, h = win.get_size()
hbox.set_position(w-250)
ktbl.view.grab_focus()
gtk.main()
