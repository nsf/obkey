#!/usr/bin/python
import xml.dom.minidom
import sys
import os
import openboxutils
import gtk
import gobject

def die(widget, data=None):
	gtk.main_quit()

# get menu file
path = os.getenv("HOME") + "/.config/openbox/rc.xml"
if len(sys.argv) == 2:
	path = sys.argv[1]

#!!!!!!!!!!!!!!!! DEVELOPMENT VERSION !!!!!!!!!!!!!!!!!!!!!!
if not os.path.exists(path+".bak"):
	os.system("cp {0} {0}.bak".format(path))
#-----------------------------------------------------------

ob = openboxutils.OpenboxConfig()
ob.load(path)

win = gtk.Window(gtk.WINDOW_TOPLEVEL)
win.set_default_size(640,480)
win.connect("destroy", die)

tbl = openboxutils.PropertyTable()
al = openboxutils.ActionList(tbl)
ktbl = openboxutils.KeyTable(al, ob)

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
