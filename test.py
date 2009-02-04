#!/usr/bin/python
import xml.dom.minidom
import sys
import openboxutils

dom = xml.dom.minidom.parse("rc.xml")

keys = []

keyboard = dom.documentElement.getElementsByTagName("keyboard")[0]

import gtk
import gobject

replace_table = {
  "mod1" : "<Mod1>",
  "mod2" : "<Mod2>",
  "mod3" : "<Mod3>",
  "mod4" : "<Mod4>",
  "mod5" : "<Mod5>",
  "control" : "<Ctrl>",
  "c" : "<Ctrl>",
  "alt" : "<Alt>",
  "a" : "<Alt>",
  "meta" : "<Meta>",
  "m" : "<Meta>",
  "super" : "<Super>",
  "w" : "<Super>",
  "shift" : "<Shift>",
  "s" : "<Shift>",
  "hyper" : "<Hyper>",
  "h" : "<Hyper>"
}

def convert_key(obstr):
	toks = obstr.split("-")
	toksgdk = [replace_table[mod.lower()] for mod in toks[:-1]]
	toksgdk.append(toks[-1])
	return gtk.accelerator_parse("".join(toksgdk))

for i in keyboard.getElementsByTagName("keybind"):
	k = i.getAttribute("key")
	print k
	k1, k2 = convert_key(k)
	keys.append((k1, k2, k))

def create_model():
	model = gtk.TreeStore(gobject.TYPE_INT, # accel mod
				gobject.TYPE_UINT, #accel key
				gobject.TYPE_STRING, # accel string
				gobject.TYPE_BOOLEAN) # chroot
	for k in keys:
		model.append(None, (k[1], k[0], k[2], False))
	return model

def c0_edited(renderer, path, accel_key, accel_mods, keycode, model):
	model[path][0] = accel_mods
	model[path][1] = accel_key

def c1_edited(renderer, path, text, model):
	model[path][1], model[path][0] = convert_key(text)
	model[path][2] = text

def c2_edited(renderer, path, model):
	model[path][3] = not model[path][3]

def create_view(model):
	view = gtk.TreeView(model)

	r0 = gtk.CellRendererAccel()
	#r0.set_property('accel-mode', gtk.CELL_RENDERER_ACCEL_MODE_OTHER)
	r0.props.editable = True
	r0.connect('accel-edited', c0_edited, model)

	r1 = gtk.CellRendererText()
	r1.props.editable = True
	r1.connect('edited', c1_edited, model)

	r2 = gtk.CellRendererToggle()
	r2.connect('toggled', c2_edited, model)

	c0 = gtk.TreeViewColumn("Key", r0, accel_key=1, accel_mods=0)
	c1 = gtk.TreeViewColumn("Key (textual)", r1, text=2)
	c2 = gtk.TreeViewColumn("Chroot", r2, active=3)

	c0.set_expand(True)
	view.append_column(c0)
	view.append_column(c1)
	view.append_column(c2)
	return view

def die(widget, data=None):
	gtk.main_quit()

ob = openboxutils.OpenboxConfig()
ob.load("rc.xml")

win = gtk.Window(gtk.WINDOW_TOPLEVEL)
win.set_default_size(640,480)
win.connect("destroy", die)

mdl = create_model()
viw = create_view(mdl)

scr = gtk.ScrolledWindow()
scr.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
scr.add_with_viewport(viw)

hbox = gtk.HPaned()
hbox.pack1(scr, True, False)

tbl = openboxutils.PropertyTable()

vbox = gtk.VPaned()
vbox.pack1(tbl.widget, True, False)

al = openboxutils.ActionList(tbl)
al.set_keybind(ob.keyboard.keybinds[0])

vbox.pack2(al.widget, True, False)
hbox.pack2(vbox, False, False)

win.add(hbox)
win.show_all()
# get rid of stupid autocalculation
hbox.set_position(hbox.get_position())
gtk.main()
