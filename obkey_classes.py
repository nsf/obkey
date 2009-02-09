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

import xml.dom.minidom
import gtk
import gobject
import os

#=====================================================================================
# Key utils
#=====================================================================================

replace_table_openbox2gtk = {
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

replace_table_gtk2openbox = {
  "Mod1" : "Mod1",
  "Mod2" : "Mod2",
  "Mod3" : "Mod3",
  "Mod4" : "Mod4",
  "Mod5" : "Mod5",
  "Control" : "C",
  "Alt" : "A",
  "Meta" : "M",
  "Super" : "W",
  "Shift" : "S",
  "Hyper" : "H"
}

def key_openbox2gtk(obstr):
	toks = obstr.split("-")
	toksgdk = [replace_table_openbox2gtk[mod.lower()] for mod in toks[:-1]]
	toksgdk.append(toks[-1])
	return gtk.accelerator_parse("".join(toksgdk))

def key_gtk2openbox(key, mods):
	result = ""
	if mods:
		s = gtk.accelerator_name(0, mods)
		svec = [replace_table_gtk2openbox[i] for i in s[1:-1].split('><')]
		result = '-'.join(svec)
	if key:
		k = gtk.accelerator_name(key, 0)
		if result != "":
			result += '-'
		result += k
	return result

#=====================================================================================
# KeyTable
#=====================================================================================

class KeyTable:
	def __init__(self, actionlist, ob):
		self.widget = gtk.VBox()
		self.ob = ob
		self.actionlist = actionlist
		self.actionlist.actions_cb = self.actions_cb

		# self.model
		# self.cqk_model
		self.create_models()

		# self.view
		# self.scroll
		# self.cqk_view
		self.create_views_and_scroll()

		# self.toolbar
		# self.add_child_button
		self.create_toolbar()

		# self.context_menu
		self.create_context_menu()

		for kb in self.ob.keyboard.keybinds:
			self.apply_keybind(kb)

		if len(self.model):
			self.view.get_selection().select_iter(self.model.get_iter_first())

		cqk_accel_key, cqk_accel_mods = key_openbox2gtk(self.ob.keyboard.chainQuitKey)
		self.cqk_model.append((cqk_accel_key, cqk_accel_mods, self.ob.keyboard.chainQuitKey))

		self.cqk_hbox = gtk.HBox()
		cqk_label = gtk.Label("chainQuitKey:")
		cqk_label.set_padding(5,5)

		cqk_frame = gtk.Frame()
		cqk_frame.add(self.cqk_view)

		self.cqk_hbox.pack_start(cqk_label, False)
		self.cqk_hbox.pack_start(cqk_frame)

		self.widget.pack_start(self.toolbar, False)
		self.widget.pack_start(self.scroll)
		self.widget.pack_start(self.cqk_hbox, False)

	def apply_keybind(self, kb, parent=None):
		accel_key, accel_mods = key_openbox2gtk(kb.key)
		chroot = kb.chroot
		show_chroot = len(kb.children) > 0
		n = self.model.append(parent,
				(accel_key, accel_mods, kb.key, chroot, show_chroot, kb))
		for c in kb.children:
			self.apply_keybind(c, n)

	def create_context_menu(self):
		self.context_menu = gtk.Menu()

		item = gtk.ImageMenuItem(gtk.STOCK_CUT)
		self.context_menu.append(item)
		item = gtk.ImageMenuItem(gtk.STOCK_COPY)
		self.context_menu.append(item)
		item = gtk.ImageMenuItem(gtk.STOCK_PASTE)
		self.context_menu.append(item)
		item = gtk.ImageMenuItem(gtk.STOCK_DELETE)
		self.context_menu.append(item)
		self.context_menu.show_all()

	def create_models(self):
		self.model = gtk.TreeStore(gobject.TYPE_UINT, # accel key
					gobject.TYPE_INT, # accel mods
					gobject.TYPE_STRING, # accel string (openbox)
					gobject.TYPE_BOOLEAN, # chroot
					gobject.TYPE_BOOLEAN, # show chroot
					gobject.TYPE_PYOBJECT # OBKeyBind
					)

		self.cqk_model = gtk.ListStore(gobject.TYPE_UINT, # accel key
						gobject.TYPE_INT, # accel mods
						gobject.TYPE_STRING) # accel string (openbox)

	def create_views_and_scroll(self):
		r0 = gtk.CellRendererAccel()
		r0.props.editable = True
		r0.connect('accel-edited', self.accel_edited)

		r1 = gtk.CellRendererText()
		r1.props.editable = True
		r1.connect('edited', self.key_edited)

		r2 = gtk.CellRendererToggle()
		r2.connect('toggled', self.chroot_toggled)

		c0 = gtk.TreeViewColumn("Key", r0, accel_key=0, accel_mods=1)
		c1 = gtk.TreeViewColumn("Key (text)", r1, text=2)
		c2 = gtk.TreeViewColumn("Chroot", r2, active=3, visible=4)

		c0.set_expand(True)

		self.view = gtk.TreeView(self.model)
		self.view.append_column(c0)
		self.view.append_column(c1)
		self.view.append_column(c2)
		self.view.get_selection().connect('changed', self.view_cursor_changed)
		self.view.connect('button-press-event', self.view_button_clicked)

		self.scroll = gtk.ScrolledWindow()
		self.scroll.add(self.view)
		self.scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		# chainQuitKey table (wtf hack)

		r0 = gtk.CellRendererAccel()
		r0.props.editable = True
		r0.connect('accel-edited', self.cqk_accel_edited)

		r1 = gtk.CellRendererText()
		r1.props.editable = True
		r1.connect('edited', self.cqk_key_edited)

		c0 = gtk.TreeViewColumn("Key", r0, accel_key=0, accel_mods=1)
		c1 = gtk.TreeViewColumn("Key (text)", r1, text=2)

		c0.set_expand(True)

		def cqk_view_focus_lost(view, event):
			view.get_selection().unselect_all()

		self.cqk_view = gtk.TreeView(self.cqk_model)
		self.cqk_view.set_headers_visible(False)
		self.cqk_view.append_column(c0)
		self.cqk_view.append_column(c1)
		self.cqk_view.connect('focus-out-event', cqk_view_focus_lost)

	def create_toolbar(self):
		self.toolbar = gtk.Toolbar()
		self.toolbar.set_style(gtk.TOOLBAR_ICONS)
		#self.toolbar.set_icon_size(gtk.ICON_SIZE_SMALL_TOOLBAR)
		self.toolbar.set_show_arrow(False)

		but = gtk.ToolButton(gtk.STOCK_SAVE)
		but.connect('clicked', lambda but: self.ob.save())
		self.toolbar.insert(but, -1)

		self.toolbar.insert(gtk.SeparatorToolItem(), -1)

		but = gtk.ToolButton(gtk.STOCK_ADD)
		but.connect('clicked', lambda but: self.add_sibling())
		self.toolbar.insert(but, -1)

		self.add_child_button = gtk.ToolButton(gtk.STOCK_GO_FORWARD)
		self.add_child_button.connect('clicked', lambda but: self.add_child())
		self.toolbar.insert(self.add_child_button, -1)

		but = gtk.ToolButton(gtk.STOCK_REMOVE)
		but.connect('clicked', lambda but: self.del_selected())
		self.toolbar.insert(but, -1)

		sep = gtk.SeparatorToolItem()
		sep.set_draw(False)
		sep.set_expand(True)
		self.toolbar.insert(sep, -1)

		self.toolbar.insert(gtk.SeparatorToolItem(), -1)

		but = gtk.ToolButton(gtk.STOCK_QUIT)
		but.connect('clicked', lambda but: gtk.main_quit())
		self.toolbar.insert(but, -1)

	#-----------------------------------------------------------------------------
	# callbacks

	def view_button_clicked(self, view, event):
		if event.button == 3:
			x = int(event.x)
			y = int(event.y)
			time = event.time
			pathinfo = view.get_path_at_pos(x, y)
			if pathinfo:
				path, col, cellx, celly = pathinfo
				view.grab_focus()
				view.set_cursor(path, col, 0)
				self.context_menu.popup(None, None, None, event.button, time)
			return 1

	def actions_cb(self):
		(model, it) = self.view.get_selection().get_selected()
		kb = model.get_value(it, 5)
		if len(kb.actions) == 0:
			model.set_value(it, 4, True)
			self.add_child_button.set_sensitive(True)
		else:
			model.set_value(it, 4, False)
			self.add_child_button.set_sensitive(False)

	def view_cursor_changed(self, selection):
		(model, it) = selection.get_selected()
		actions = None
		if it:
			kb = model.get_value(it, 5)
			if len(kb.children) == 0 and not kb.chroot:
				actions = kb.actions
			self.add_child_button.set_sensitive(len(kb.actions) == 0)
		else:
			self.add_child_button.set_sensitive(False)
		self.actionlist.set_actions(actions)

	def cqk_accel_edited(self, cell, path, accel_key, accel_mods, keycode):
		self.cqk_model[path][0] = accel_key
		self.cqk_model[path][1] = accel_mods
		kstr = key_gtk2openbox(accel_key, accel_mods)
		self.cqk_model[path][2] = kstr
		self.ob.keyboard.chainQuitKey = kstr
		self.view.grab_focus()

	def cqk_key_edited(self, cell, path, text):
		self.cqk_model[path][0], self.cqk_model[path][1] = key_openbox2gtk(text)
		self.cqk_model[path][2] = text
		self.ob.keyboard.chainQuitKey = text
		self.view.grab_focus()

	def accel_edited(self, cell, path, accel_key, accel_mods, keycode):
		self.model[path][0] = accel_key
		self.model[path][1] = accel_mods
		kstr = key_gtk2openbox(accel_key, accel_mods)
		self.model[path][2] = kstr
		self.model[path][5].key = kstr

	def key_edited(self, cell, path, text):
		self.model[path][0], self.model[path][1] = key_openbox2gtk(text)
		self.model[path][2] = text
		self.model[path][5].key = text

	def chroot_toggled(self, cell, path):
		self.model[path][3] = not self.model[path][3]
		kb = self.model[path][5]
		kb.chroot = self.model[path][3]
		if kb.chroot:
			self.actionlist.set_actions(None)
		else:
			self.actionlist.set_actions(kb.actions)

	#-----------------------------------------------------------------------------
	def add_sibling(self):
		(model, it) = self.view.get_selection().get_selected()
		parent_it = model.iter_parent(it)
		parent = None
		if parent_it:
			parent = model.get_value(parent_it, 5)
		if it:
			newkb = self.insert_empty_keybind(parent, model.get_value(it, 5))
			newit = self.model.insert_after(parent_it, it, (ord('a'), 0, 'a', False, True, newkb))
		else:
			newkb = self.insert_empty_keybind()
			newit = self.model.append(None, (ord('a'), 0, 'a', False, True, newkb))

		if newit:
			self.view.get_selection().select_iter(newit)

	def add_child(self):
		(model, it) = self.view.get_selection().get_selected()
		parent = model.get_value(it, 5)
		newkb = self.insert_empty_keybind(parent)
		newit = self.model.append(it, (ord('a'), 0, 'a', False, True, newkb))
		if len(parent.children) == 1:
			self.actionlist.set_actions(None)

	def del_selected(self):
		(model, it) = self.view.get_selection().get_selected()
		if it:
			kb = model.get_value(it, 5)
			kbs = self.ob.keyboard.keybinds
			if kb.parent:
				kbs = kb.parent.children
			kbs.remove(kb)
			isok = self.model.remove(it)
			if isok:
				self.view.get_selection().select_iter(it)

	def insert_empty_keybind(self, parent=None, after=None):
		newkb = OBKeyBind(parent)
		if parent:
			kbs = parent.children
		else:
			kbs = self.ob.keyboard.keybinds

		if after:
			kbs.insert(kbs.index(after)+1, newkb)
		else:
			kbs.append(newkb)
		return newkb

#=====================================================================================
# PropertyTable
#=====================================================================================

class PropertyTable:
	def __init__(self):
		self.widget = gtk.ScrolledWindow()
		self.table = gtk.Table(1,2)
		self.table.set_row_spacings(5)
		self.widget.add_with_viewport(self.table)
		self.widget.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

	def add_row(self, label_text, table):
		label = gtk.Label(label_text)
		label.set_alignment(0, 0)
		row = self.table.props.n_rows
		self.table.attach(label, 0, 1, row, row+1, gtk.EXPAND | gtk.FILL, 0, 5, 0)
		self.table.attach(table, 1, 2, row, row+1, gtk.FILL, 0, 5, 0)

	def clear(self):
		cs = self.table.get_children()
		cs.reverse()
		for c in cs:
			self.table.remove(c)
		self.table.resize(1, 2)

	def set_action(self, action):
		self.clear()
		if not action:
			return
		for a in action.option_defs:
			self.add_row(a.name + ":", a.generate_widget(action))
		self.table.queue_resize()
		self.table.show_all()

#=====================================================================================
# ActionList
#=====================================================================================

class ActionList:
	def __init__(self, proptable=None):
		self.widget = gtk.VBox()
		self.actions = None
		self.proptable = proptable

		# actions callback, called when action added or deleted
		# for chroot possibility tracing
		self.actions_cb = None

		self.create_model()
		self.create_choices()
		self.create_view_and_scroll()
		self.create_toolbar()

		self.widget.pack_start(self.scroll)
		self.widget.pack_start(self.toolbar, False)

	def create_model(self):
		self.model = gtk.ListStore(gobject.TYPE_STRING, # name of the action
					gobject.TYPE_PYOBJECT) # associated OBAction

	def create_choices(self):
		self.choices = gtk.ListStore(gobject.TYPE_STRING)
		action_list = actions.keys();
		action_list.sort()
		for a in action_list:
			self.choices.append((a,))

	def create_view_and_scroll(self):
		# renderer
		renderer = gtk.CellRendererCombo()

		def editingstarted(cell, widget, path):
			widget.set_wrap_width(4)

		# action list
		renderer.props.model = self.choices
		renderer.props.text_column = 0
		renderer.props.editable = True
		renderer.props.has_entry = False
		renderer.connect('changed', self.action_class_changed)
		renderer.connect('editing-started', editingstarted)

		# column
		column = gtk.TreeViewColumn("Actions", renderer, text=0)

		# view
		self.view = gtk.TreeView(self.model)
		self.view.append_column(column)
		self.view.get_selection().connect('changed', self.view_cursor_changed)

		# scrolled window == the "real" view
		self.scroll = gtk.ScrolledWindow()
		self.scroll.add(self.view)
		self.scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

	def create_toolbar(self):
		self.toolbar = gtk.Toolbar()
		self.toolbar.set_style(gtk.TOOLBAR_ICONS)
		self.toolbar.set_icon_size(gtk.ICON_SIZE_SMALL_TOOLBAR)
		self.toolbar.set_show_arrow(False)

		but = gtk.ToolButton(gtk.STOCK_ADD)
		but.connect('clicked', self.tb_add_clicked)
		self.toolbar.insert(but, -1)

		but = gtk.ToolButton(gtk.STOCK_REMOVE)
		but.connect('clicked', self.tb_del_clicked)
		self.toolbar.insert(but, -1)

		but = gtk.ToolButton(gtk.STOCK_GO_UP)
		but.connect('clicked', self.tb_up_clicked)
		self.toolbar.insert(but, -1)

		but = gtk.ToolButton(gtk.STOCK_GO_DOWN)
		but.connect('clicked', self.tb_down_clicked)
		self.toolbar.insert(but, -1)

	#-----------------------------------------------------------------------------
	# callbacks

	def action_class_changed(self, combo, path, it):
		m = combo.props.model
		ntype = m.get_value(it, 0)
		self.model[path][0] = ntype
		self.model[path][1].mutate(ntype)
		if self.proptable:
			self.proptable.set_action(self.model[path][1])

	def view_cursor_changed(self, selection):
		(model, it) = selection.get_selected()
		act = None
		if it:
			act = model.get_value(it, 1)
		if self.proptable:
			self.proptable.set_action(act)

	def tb_up_clicked(self, button):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if not it:
			return

		i, = self.model.get_path(it)
		if i == 0:
			return

		itprev = self.model.get_iter(i-1)
		self.model.swap(it, itprev)
		self.move_up(self.model.get_value(it, 1))

	def tb_down_clicked(self, button):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if not it:
			return

		i, = self.model.get_path(it)
		if i+1 >= len(self.model):
			return

		itnext = self.model.iter_next(it)
		self.model.swap(it, itnext)
		self.move_down(self.model.get_value(it, 1))

	def tb_add_clicked(self, button):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if it:
			oba = self.insert_empty_action(model.get_value(it, 1))
			newit = self.model.insert_after(it, (oba.name, oba))
		else:
			oba = self.insert_empty_action()
			newit = self.model.append((oba.name, oba))

		if newit:
			self.view.get_selection().select_iter(newit)

		if self.actions_cb:
			self.actions_cb()

	def tb_del_clicked(self, button):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if it:
			self.actions.remove(model.get_value(it, 1))
			isok = self.model.remove(it)
			if isok:
				self.view.get_selection().select_iter(it)

		if self.actions_cb:
			self.actions_cb()

	#-----------------------------------------------------------------------------

	def set_actions(self, actionlist):
		self.actions = actionlist
		self.model.clear()
		if not self.actions:
			return
		for a in self.actions:
			self.model.append((a.name, a))
		if len(self.model):
			self.view.get_selection().select_iter(self.model.get_iter_first())

	def insert_empty_action(self, after=None):
		newact = OBAction()
		newact.mutate("Execute")

		if after:
			self.actions.insert(self.actions.index(after)+1, newact)
		else:
			self.actions.append(newact)
		return newact

	def move_up(self, action):
		i = self.actions.index(action)
		tmp = self.actions[i-1]
		self.actions[i-1] = action
		self.actions[i] = tmp

	def move_down(self, action):
		i = self.actions.index(action)
		tmp = self.actions[i+1]
		self.actions[i+1] = action
		self.actions[i] = tmp

#=====================================================================================
# MiniActionList
#=====================================================================================

class MiniActionList(ActionList):
	def __init__(self, proptable=None):
		ActionList.__init__(self, proptable)
		self.widget.set_size_request(-1, 120)
		self.view.set_headers_visible(False)

	def create_choices(self):
		self.choices = gtk.ListStore(gobject.TYPE_STRING)
		action_list = actions.keys();
		action_list.sort()
		for a in action_list:
			if len(actions[a]) == 0:
				self.choices.append((a,))

	def insert_empty_action(self, after=None):
		newact = OBAction()
		newact.mutate("Unshade")

		if after:
			self.actions.insert(self.actions.index(after)+1, newact)
		else:
			self.actions.append(newact)
		return newact

#=====================================================================================
# XML Utilites
#=====================================================================================
# parse

def xml_parse_attr(elt, name):
	return elt.getAttribute(name)

def xml_parse_attr_bool(elt, name):
	attr = elt.getAttribute(name).lower()
	if attr == "true" or attr == "yes" or attr == "on":
		return True
	return False

def xml_parse_string(elt):
	return elt.firstChild.nodeValue

def xml_parse_bool(elt):
	val = elt.firstChild.nodeValue.lower()
	if val == "true" or val == "yes" or val == "on":
		return True
	return False

def xml_find_nodes(elt, name):
	children = []
	for n in elt.childNodes:
		if n.nodeName == name:
			children.append(n)
	return children

def xml_find_node(elt, name):
	nodes = xml_find_nodes(elt, name)
	if len(nodes) == 1:
		return nodes[0]
	else:
		return None

#=====================================================================================
# Openbox Glue
#=====================================================================================

# Option Classes (for OBAction)
# 1. Parse function for OBAction to parse the data.
# 2. Getter(s) and Setter(s) for OBAction to operate on the data (registered by 
# the parse function).
# 3. Widget generator for property editor to represent the data.
# Examples of such classes: string, int, filename, list of actions, 
# list (choose one variant of many), string-int with custom validator(?)

# Actions
# An array of Options: <option_name> + <option_class>
# These actions are being applied to OBAction instances.

#=====================================================================================
# Option Class: String
#=====================================================================================

class OCString(object):
	__slots__ = ('name', 'default', 'alts')

	def __init__(self, name, default, alts=[]):
		self.name = name
		self.default = default
		self.alts = alts

	def apply_default(self, action):
		action.options[self.name] = self.default

	def parse(self, action, dom):
		node = xml_find_node(dom, self.name)
		if not node:
			for a in self.alts:
				node = xml_find_node(dom, a)
				if node:
					break
		if node:
			action.options[self.name] = xml_parse_string(node)
		else:
			action.options[self.name] = self.default

	def deparse(self, action):
		val = action.options[self.name]
		if val == self.default:
			return None
		return xml.dom.minidom.parseString("<{0}>{1}</{0}>"
				.format(self.name, val)).documentElement

	def generate_widget(self, action):
		def changed(entry, action):
			text = entry.get_text()
			action.options[self.name] = text

		entry = gtk.Entry()
		entry.set_text(action.options[self.name])
		entry.connect('changed', changed, action)
		return entry

#=====================================================================================
# Option Class: Combo
#=====================================================================================

class OCCombo(object):
	__slots__ = ('name', 'default', 'choices')

	def __init__(self, name, default, choices):
		self.name = name
		self.default = default
		self.choices = choices

	def apply_default(self, action):
		action.options[self.name] = self.default

	def parse(self, action, dom):
		node = xml_find_node(dom, self.name)
		if not node:
			for a in self.alts:
				node = xml_find_node(dom, a)
				if node:
					break
		if node:
			action.options[self.name] = xml_parse_string(node)
		else:
			action.options[self.name] = self.default

	def deparse(self, action):
		val = action.options[self.name]
		if val == self.default:
			return None
		return xml.dom.minidom.parseString("<{0}>{1}</{0}>"
				.format(self.name, val)).documentElement

	def generate_widget(self, action):
		def changed(combo, action):
			text = combo.get_active()
			action.options[self.name] = self.choices[text]

		model = gtk.ListStore(gobject.TYPE_STRING)
		for c in self.choices:
			model.append((c,))

		combo = gtk.ComboBox()
		combo.set_active(self.choices.index(action.options[self.name]))
		combo.set_model(model)
		cell = gtk.CellRendererText()
		combo.pack_start(cell, True)
		combo.add_attribute(cell, 'text', 0)
		combo.connect('changed', changed, action)
		return combo

#=====================================================================================
# Option Class: Number
#=====================================================================================

class OCNumber(object):
	__slots__ = ('name', 'default', 'min', 'max')

	def __init__(self, name, default, mmin, mmax):
		self.name = name
		self.default = default
		self.min = mmin
		self.max = mmax

	def apply_default(self, action):
		action.options[self.name] = self.default

	def parse(self, action, dom):
		node = xml_find_node(dom, self.name)
		if node:
			action.options[self.name] = int(float(xml_parse_string(node)))
		else:
			action.options[self.name] = self.default

	def deparse(self, action):
		val = action.options[self.name]
		if val == self.default:
			return None
		return xml.dom.minidom.parseString("<{0}>{1}</{0}>"
				.format(self.name, val)).documentElement

	def generate_widget(self, action):
		def changed(num, action):
			n = num.get_value_as_int()
			action.options[self.name] = n

		num = gtk.SpinButton()
		num.set_increments(1, 5)
		num.set_range(self.min, self.max)
		num.set_value(action.options[self.name])
		num.connect('value-changed', changed, action)
		return num

#=====================================================================================
# Option Class: Boolean
#=====================================================================================

class OCBoolean(object):
	__slots__ = ('name', 'default')

	def __init__(self, name, default):
		self.name = name
		self.default = default

	def apply_default(self, action):
		action.options[self.name] = self.default

	def parse(self, action, dom):
		node = xml_find_node(dom, self.name)
		if node:
			action.options[self.name] = xml_parse_bool(node)
		else:
			action.options[self.name] = self.default

	def deparse(self, action):
		if action.options[self.name] == self.default:
			return None
		if action.options[self.name]:
			return xml.dom.minidom.parseString("<{0}>yes</{0}>"
					.format(self.name)).documentElement
		else:
			return xml.dom.minidom.parseString("<{0}>no</{0}>"
					.format(self.name)).documentElement

	def generate_widget(self, action):
		def changed(checkbox, action):
			active = checkbox.get_active()
			action.options[self.name] = active

		check = gtk.CheckButton()
		check.set_active(action.options[self.name])
		check.connect('toggled', changed, action)
		return check

#=====================================================================================
# Option Class: StartupNotify
#=====================================================================================

class OCStartupNotify(object):
	def __init__(self):
		self.name = "startupnotify"

	def apply_default(self, action):
		action.options['startupnotify_enabled'] = False
		action.options['startupnotify_wmclass'] = ""
		action.options['startupnotify_name'] = ""
		action.options['startupnotify_icon'] = ""

	def parse(self, action, dom):
		self.apply_default(action)

		startupnotify = xml_find_node(dom, "startupnotify")
		if not startupnotify:
			return

		enabled = xml_find_node(startupnotify, "enabled")
		if enabled:
			action.options['startupnotify_enabled'] = xml_parse_bool(enabled)
		wmclass = xml_find_node(startupnotify, "wmclass")
		if wmclass:
			action.options['startupnotify_wmclass'] = xml_parse_string(wmclass)
		name = xml_find_node(startupnotify, "name")
		if name:
			action.options['startupnotify_name'] = xml_parse_string(name)
		icon = xml_find_node(startupnotify, "icon")
		if icon:
			action.options['startupnotify_icon'] = xml_parse_string(icon)

	def deparse(self, action):
		if not action.options['startupnotify_enabled']:
			return None
		root = xml.dom.minidom.parseString("<startupnotify><enabled>yes</enabled></startupnotify>").documentElement
		if action.options['startupnotify_wmclass'] != "":
			root.appendChild(xml.dom.minidom.parseString("<wmclass>{0}</wmclass>".format(action.options['startupnotify_wmclass'])).documentElement)
		if action.options['startupnotify_name'] != "":
			root.appendChild(xml.dom.minidom.parseString("<name>{0}</name>".format(action.options['startupnotify_name'])).documentElement)
		if action.options['startupnotify_icon'] != "":
			root.appendChild(xml.dom.minidom.parseString("<icon>{0}</icon>".format(action.options['startupnotify_icon'])).documentElement)
		return root

	def generate_widget(self, action):
		def enabled_toggled(checkbox, action, sens_list):
			active = checkbox.get_active()
			action.options['startupnotify_enabled'] = active
			for w in sens_list:
				w.set_sensitive(active)

		def text_changed(textbox, action, var):
			text = textbox.get_text()
			action.options[var] = text


		wmclass = gtk.Entry()
		wmclass.set_size_request(100,-1)
		wmclass.set_text(action.options['startupnotify_wmclass'])
		wmclass.connect('changed', text_changed, action, 'startupnotify_wmclass')

		name = gtk.Entry()
		name.set_size_request(100,-1)
		name.set_text(action.options['startupnotify_name'])
		name.connect('changed', text_changed, action, 'startupnotify_name')

		icon = gtk.Entry()
		icon.set_size_request(100,-1)
		icon.set_text(action.options['startupnotify_icon'])
		icon.connect('changed', text_changed, action, 'startupnotify_icon')

		sens_list = [wmclass, name, icon]

		enabled = gtk.CheckButton()
		enabled.set_active(action.options['startupnotify_enabled'])
		enabled.connect('toggled', enabled_toggled, action, sens_list)

		def put_table(table, label_text, widget, row, addtosens=True):
			label = gtk.Label(label_text)
			label.set_padding(5,5)
			label.set_alignment(0,0)
			if addtosens:
				sens_list.append(label)
			table.attach(label, 0, 1, row, row+1, gtk.EXPAND | gtk.FILL, 0, 0, 0)
			table.attach(widget, 1, 2, row, row+1, gtk.FILL, 0, 0, 0)

		table = gtk.Table(1, 2)
		put_table(table, "enabled:", enabled, 0, False)
		put_table(table, "wmclass:", wmclass, 1)
		put_table(table, "name:", name, 2)
		put_table(table, "icon:", icon, 3)

		sens = enabled.get_active()
		for w in sens_list:
			w.set_sensitive(sens)

		frame = gtk.Frame()
		frame.add(table)
		return frame

#=====================================================================================
# Option Class: FinalActions
#=====================================================================================

class OCFinalActions(object):
	__slots__ = ('name')

	def __init__(self):
		self.name = "finalactions"

	def apply_default(self, action):
		a1 = OBAction()
		a1.mutate("Focus")
		a2 = OBAction()
		a2.mutate("Raise")
		a3 = OBAction()
		a3.mutate("Unshade")

		action.options[self.name] = [a1, a2, a3]

	def parse(self, action, dom):
		node = xml_find_node(dom, self.name)
		action.options[self.name] = []
		if node:
			for a in xml_find_nodes(node, "action"):
				act = OBAction()
				act.parse(a)
				action.options[self.name].append(act)
		else:
			self.apply_default(action)

	def deparse(self, action):
		a = action.options[self.name]
		if len(a) == 3:
			if a[0].name == "Focus" and a[1].name == "Raise" and a[2].name == "Unshade":
				return None
		if len(a) == 0:
			return None
		root = xml.dom.minidom.parseString("<finalactions/>").documentElement
		for act in a:
			node = act.deparse()
			root.appendChild(node)
		return root

	def generate_widget(self, action):
		w = MiniActionList()
		w.set_actions(action.options[self.name])
		frame = gtk.Frame()
		frame.add(w.widget)
		return frame

#-------------------------------------------------------------------------------------

actions = {
	"Execute": [
		OCString("command", "", ['execute']),
		OCString("prompt", ""),
		OCStartupNotify()
	],
	"ShowMenu": [
		OCString("menu", "")
	],
	"NextWindow": [
		OCBoolean("dialog", True),
		OCBoolean("bar", True),
		OCBoolean("raise", False),
		OCBoolean("allDesktops", False),
		OCBoolean("panels", False),
		OCBoolean("desktop", False),
		OCBoolean("linear", False),
		OCFinalActions()
	],
	"PreviousWindow": [
		OCBoolean("dialog", True),
		OCBoolean("bar", True),
		OCBoolean("raise", False),
		OCBoolean("allDesktops", False),
		OCBoolean("panels", False),
		OCBoolean("desktop", False),
		OCBoolean("linear", False),
		OCFinalActions()
	],
	"DirectionalFocusNorth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalFocusSouth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalFocusEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalFocusWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalFocusNorthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalFocusNorthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalFocusSouthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalFocusSouthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetNorth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetSouth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetNorthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetNorthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetSouthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"DirectionalTargetSouthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False), OCFinalActions() ],
	"Desktop": [ OCNumber("desktop", 1, 1, 9999) ],
	"DesktopNext": [ OCBoolean("wrap", True) ],
	"DesktopPrevious": [ OCBoolean("wrap", True) ],
	"DesktopLeft": [ OCBoolean("wrap", True) ],
	"DesktopRight": [ OCBoolean("wrap", True) ],
	"DesktopUp": [ OCBoolean("wrap", True) ],
	"DesktopDown": [ OCBoolean("wrap", True) ],
	"DesktopLast": [],
	"AddDesktopLast": [],
	"RemoveDesktopLast": [],
	"AddDesktopCurrent": [],
	"RemoveDesktopCurrent": [],
	"ToggleShowDesktop": [],
	"ToggleDockAutohide": [],
	"Reconfigure": [],
	"Restart": [ OCString("command", "", ["execute"]) ],
	"Exit": [ OCBoolean("prompt", True) ],
	"SessionLogout": [ OCBoolean("prompt", True) ],
	"Debug": [ OCString("string", "") ],

	"Focus": [],
	"Raise": [],
	"Lower": [],
	"RaiseLower": [],
	"Unfocus": [],
	"FocusToBottom": [],
	"Iconify": [],
	"Close": [],
	"ToggleShade": [],
	"Shade": [],
	"Unshade": [],
	"ToggleOmnipresent": [],
	"ToggleMaximizeFull": [],
	"MaximizeFull": [],
	"UnmaximizeFull": [],
	"ToggleMaximizeVert": [],
	"MaximizeVert": [],
	"UnmaximizeVert": [],
	"ToggleMaximizeHorz": [],
	"MaximizeHorz": [],
	"UnmaximizeHorz": [],
	"ToggleFullscreen": [],
	"ToggleDecorations": [],
	"Decorate": [],
	"Undecorate": [],
	"SendToDesktop": [ OCNumber("desktop", 1, 1, 9999), OCBoolean("follow", True) ],
	"SendToDesktopNext": [ OCBoolean("wrap", True), OCBoolean("follow", True) ],
	"SendToDesktopPrevious": [ OCBoolean("wrap", True), OCBoolean("follow", True) ],
	"SendToDesktopLeft": [ OCBoolean("wrap", True), OCBoolean("follow", True) ],
	"SendToDesktopRight": [ OCBoolean("wrap", True), OCBoolean("follow", True) ],
	"SendToDesktopUp": [ OCBoolean("wrap", True), OCBoolean("follow", True) ],
	"SendToDesktopDown": [ OCBoolean("wrap", True), OCBoolean("follow", True) ],
	"Move": [],
	"Resize": [
		OCCombo("edge", "none", ['none', "top", "left", "right", "bottom", "topleft", "topright", "bottomleft", "bottomright"])
	],
	"MoveToCenter": [],
	"MoveResizeTo": [
		OCString("x", "current"),
		OCString("y", "current"),
		OCString("width", "current"),
		OCString("height", "current"),
		OCString("monitor", "current")
	],
	"MoveRelative": [
		OCNumber("x", 0, -9999, 9999),
		OCNumber("y", 0, -9999, 9999)
	],
	"ResizeRelative": [
		OCNumber("left", 0, -9999, 9999),
		OCNumber("right", 0, -9999, 9999),
		OCNumber("top", 0, -9999, 9999),
		OCNumber("bottom", 0, -9999, 9999)
	],
	"MoveToEdgeNorth": [],
	"MoveToEdgeSouth": [],
	"MoveToEdgeWest": [],
	"MoveToEdgeEast": [],
	"GrowToEdgeNorth": [],
	"GrowToEdgeSouth": [],
	"GrowToEdgeWest": [],
	"GrowToEdgeEast": [],
	"ShadeLower": [],
	"UnshadeRaise": [],
	"ToggleAlwaysOnTop": [],
	"ToggleAlwaysOnBottom": [],
	"SendToTopLayer": [],
	"SendToBottomLayer": [],
	"SendToNormalLayer": [],

	"BreakChroot": []
}

#=====================================================================================
# Config parsing and interaction
#=====================================================================================

class OBAction:
	def __init__(self):
		self.options = {}
		self.option_defs = []
		self.name = None

	def parse(self, dom):
		# parse 'name' attribute, get options hash and parse
		self.name = xml_parse_attr(dom, "name")

		try:
			self.option_defs = actions[self.name]
		except KeyError:
			pass

		for od in self.option_defs:
			od.parse(self, dom)

	def deparse(self):
		root = xml.dom.minidom.parseString('<action name="{0}"/>'.format(self.name)).documentElement
		for od in self.option_defs:
			od_node = od.deparse(self)
			if od_node:
				root.appendChild(od_node)
		return root

	def mutate(self, newtype):
		if hasattr(self, "option_defs") and actions[newtype] == self.option_defs:
			self.options = {}
			self.name = newtype
			return

		self.options = {}
		self.name = newtype
		self.option_defs = actions[self.name]

		for od in self.option_defs:
			od.apply_default(self)

#-------------------------------------------------------------------------------------

class OBKeyBind:
	def __init__(self, parent=None):
		self.children = []
		self.actions = []
		self.key = "a"
		self.chroot = False
		self.parent = parent

	def parse(self, dom):
		self.key = xml_parse_attr(dom, "key")
		self.chroot = xml_parse_attr_bool(dom, "chroot")

		kbinds = xml_find_nodes(dom, "keybind")
		if len(kbinds):
			for k in kbinds:
				kb = OBKeyBind(self)
				kb.parse(k)
				self.children.append(kb)
		else:
			for a in xml_find_nodes(dom, "action"):
				newa = OBAction()
				newa.parse(a)
				self.actions.append(newa)

	def deparse(self):
		if self.chroot:
			root = xml.dom.minidom.parseString('<keybind key="{0}" chroot="yes"/>'
				.format(self.key)).documentElement
		else:
			root = xml.dom.minidom.parseString('<keybind key="{0}"/>'
				.format(self.key)).documentElement

		if len(self.children):
			for k in self.children:
				root.appendChild(k.deparse())
		else:
			for a in self.actions:
				root.appendChild(a.deparse())
		return root

	def insert_empty_action(self, after=None):
		newact = OBAction()
		newact.mutate("Execute")

		if after:
			self.actions.insert(self.actions.index(after)+1, newact)
		else:
			self.actions.append(newact)
		return newact

	def move_up(self, action):
		i = self.actions.index(action)
		tmp = self.actions[i-1]
		self.actions[i-1] = action
		self.actions[i] = tmp

	def move_down(self, action):
		i = self.actions.index(action)
		tmp = self.actions[i+1]
		self.actions[i+1] = action
		self.actions[i] = tmp


#-------------------------------------------------------------------------------------

class OBKeyboard:
	def __init__(self, dom):
		self.chainQuitKey = None
		self.keybinds = []

		cqk = xml_find_node(dom, "chainQuitKey")
		if cqk:
			self.chainQuitKey = xml_parse_string(cqk)

		for keybind_node in xml_find_nodes(dom, "keybind"):
			kb = OBKeyBind()
			kb.parse(keybind_node)
			self.keybinds.append(kb)

	def deparse(self):
		root = xml.dom.minidom.parseString('<keyboard/>').documentElement
		chainQuitKey_node = xml.dom.minidom.parseString(
				'<chainQuitKey>{0}</chainQuitKey>'.format(self.chainQuitKey)).documentElement
		root.appendChild(chainQuitKey_node)

		for k in self.keybinds:
			root.appendChild(k.deparse())

		return root

#-------------------------------------------------------------------------------------

class OpenboxConfig:
	def __init__(self):
		self.dom = None
		self.keyboard = None
		self.path = None

	def load(self, path):
		self.path = path

		# load config DOM
		self.dom = xml.dom.minidom.parse(path)

		# try load keyboard DOM
		keyboard = xml_find_node(self.dom.documentElement, "keyboard")
		if keyboard:
			self.keyboard = OBKeyboard(keyboard)

	def save(self):
		if self.path is None:
			return

		# it's all hack, waste of resources etc, but does pretty good result
		keyboard = xml_find_node(self.dom.documentElement, "keyboard")
		newdom = self.keyboard.deparse()
		self.dom.documentElement.replaceChild(newdom, keyboard)
		f = file(self.path, "w")
		if f:
			f.write(self.dom.documentElement.toxml("utf-8"))
			f.close()
		self.reconfigure_openbox()

	def reconfigure_openbox(self):
		lines = os.popen("ps aux").read().splitlines()
		ob = os.popen("which openbox").read().strip()
		for line in lines:
			if ob in " ".join(line.split()[10:]):
				os.kill(int(line.split()[1]), 12)
				break
