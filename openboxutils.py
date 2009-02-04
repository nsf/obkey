#!/usr/bin/python

import xml.dom.minidom
import gtk
import gobject

#=====================================================================================
# GUI Elements
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
		for i in range(len(action.option_defs)):
			optdef = action.option_defs[i]
			self.add_row(optdef.name + ":", optdef.generate_widget(action, i))
		self.table.queue_resize()
		self.table.show_all()

#-------------------------------------------------------------------------------------

class ActionList:
	def __init__(self, proptable):
		self.proptable = proptable
		self.widget = gtk.VBox()
		self.keybind = None

		self.create_model()
		self.create_view_and_scroll()
		self.create_toolbar()

		self.widget.pack_start(self.scroll)
		self.widget.pack_start(self.toolbar, False)

	def create_model(self):
		self.model = gtk.ListStore(gobject.TYPE_STRING, # name of the action
					gobject.TYPE_PYOBJECT) # associated OBAction

	def create_view_and_scroll(self):
		# renderer
		renderer = gtk.CellRendererCombo()

		# action list
		choices = gtk.ListStore(gobject.TYPE_STRING)
		action_list = actions.keys();
		action_list.sort()
		for a in action_list:
			choices.append((a,))
		renderer.props.model = choices
		renderer.props.text_column = 0
		renderer.props.editable = True
		renderer.props.has_entry = False
		renderer.connect('changed', self.action_class_changed)

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

		but = gtk.ToolButton(gtk.STOCK_INFO)
		but.connect('clicked', self.tb_info_clicked)
		self.toolbar.insert(but, -1)

	#-----------------------------------------------------------------------------
	# callbacks

	def action_class_changed(self, combo, path, it):
		m = combo.props.model
		ntype = m.get_value(it, 0)
		self.model[path][0] = ntype
		self.model[path][1].mutate(ntype)
		self.proptable.set_action(self.model[path][1])

	def view_cursor_changed(self, selection):
		(model, it) = selection.get_selected()
		act = None
		if it:
			act = model.get_value(it, 1)
		self.proptable.set_action(act)

	def tb_up_clicked(self, button):
		if not self.keybind:
			return

		(model, it) = self.view.get_selection().get_selected()
		if not it:
			return

		i, = self.model.get_path(it)
		if i == 0:
			return

		itprev = self.model.get_iter(i-1)
		self.model.swap(it, itprev)
		self.keybind.move_up(self.model.get_value(it, 1))

	def tb_down_clicked(self, button):
		if not self.keybind:
			return

		(model, it) = self.view.get_selection().get_selected()
		if not it:
			return

		i, = self.model.get_path(it)
		if i+1 >= len(self.model):
			return

		itnext = self.model.iter_next(it)
		self.model.swap(it, itnext)
		self.keybind.move_down(self.model.get_value(it, 1))

	def tb_add_clicked(self, button):
		if not self.keybind:
			return

		(model, it) = self.view.get_selection().get_selected()
		if it:
			oba = self.keybind.insert_empty_action(model.get_value(it, 1))
			newit = self.model.insert_after(it, (oba.name, oba))
		else:
			oba = self.keybind.insert_empty_action()
			newit = self.model.append((oba.name, oba))

		if newit:
			self.view.get_selection().select_iter(newit)

	def tb_del_clicked(self, button):
		if not self.keybind:
			return

		(model, it) = self.view.get_selection().get_selected()
		if it:
			self.keybind.remove_action(model.get_value(it, 1))
			isok = self.model.remove(it)
			if isok:
				self.view.get_selection().select_iter(it)

	def tb_info_clicked(self, button):
		dom = self.keybind.dom
		print dom.toxml("utf-8")

	#-----------------------------------------------------------------------------

	def set_keybind(self, keybind):
		self.keybind = keybind
		self.model.clear()
		if not keybind:
			return
		for a in keybind.actions:
			self.model.append((a.name, a))
		if len(self.model):
			self.view.get_selection().select_iter(self.model.get_iter_first())


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
	return elt.getElementsByTagName(name)

def xml_find_node(elt, name):
	nodes = xml_find_nodes(elt, name)
	if len(nodes) == 1:
		return nodes[0]
	else:
		return None

#-------------------------------------------------------------------------------------
# change DOM

def xml_set_string(elt, string):
	elt.firstChild.nodeValue = string

def xml_set_bool(elt, b):
	if b:
		xml_set_string(elt, "yes")
	else:
		xml_set_string(elt, "no")

def xml_set_attr(elt, name, string):
	elt.setAttribute(name, string)

def xml_remove_attr(elt, name):
	try:
		elt.removeAttribute(name)
	except xml.dom.NotFoundErr:
		pass

def xml_remove_child(elt, child):
	c = elt.removeChild(child)
	c.unlink()

def xml_remove_all_children(elt):
	last = elt.lastChild
	while last:
		xml_remove_child(elt, last)
		last = elt.lastChild

def xml_insert_after(elt, new, after=None):
	if after:
		elt.insertBefore(new, after.nextSibling)
	else:
		elt.appendChild(new)

def xml_insert_textvalue_after(elt, text, value, after=None):
	newdom = xml.dom.minidom.parseString("<{0}>{1}</{0}>".format(text, value)).documentElement
	xml_insert_after(elt, newdom, after)
	return newdom

def xml_move_up(elt, what):
	upper = what.previousSibling
	tmp = elt.removeChild(what)
	elt.insertBefore(tmp, upper)

def xml_move_down(elt, what):
	down = what.nextSibling
	tmp = elt.removeChild(down)
	elt.insertBefore(tmp, what)

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

class Option(object):
	__slots__ = ('value', 'dom')

	def __init__(self, value, dom):
		self.value = value
		self.dom = dom

#=====================================================================================
# Option Class: String
#=====================================================================================

def text_changed_callback(action, i, text, value):
	optdef = action.option_defs[i]
	opt = action.options[optdef.name]

	if value == optdef.default and opt.dom:
		xml_remove_child(action.dom, opt.dom)
		opt.dom = None
	elif opt.dom:
		xml_set_string(opt.dom, text)
	else:
		prev = None
		while i >= 0:
			i -= 1
			prev = action.options[action.option_defs[i].name].dom
			if prev:
				break

		opt.dom = xml_insert_textvalue_after(action.dom, optdef.name, text, prev)
	opt.value = value


class OCString(object):
	__slots__ = ('name', 'default')

	def __init__(self, name, default):
		self.name = name
		self.default = default

	def parse(self, action):
		node = xml_find_node(action.dom, self.name)
		if node:
			action.options[self.name] = Option(xml_parse_string(node), node)
		else:
			action.options[self.name] = Option(self.default, None)

	def generate_widget(self, action, i):
		def changed(entry, action, i):
			text = entry.get_text()
			text_changed_callback(action, i, text, text)

		entry = gtk.Entry()
		entry.set_text(action.options[self.name].value)
		entry.connect('changed', changed, action, i)
		return entry

class OCBoolean(object):
	__slots__ = ('name', 'default')

	def __init__(self, name, default):
		self.name = name
		self.default = default

	def parse(self, action):
		node = xml_find_node(action.dom, self.name)
		if node:
			action.options[self.name] = Option(xml_parse_bool(node), node)
		else:
			action.options[self.name] = Option(self.default, None)

	def generate_widget(self, action, i):
		def changed(checkbox, action, i):
			active = checkbox.get_active()
			text = "no"
			if active:
				text = "yes"
			text_changed_callback(action, i, text, active)

		check = gtk.CheckButton()
		check.set_active(action.options[self.name].value)
		check.connect('toggled', changed, action, i)
		return check

#-------------------------------------------------------------------------------------

actions = {
	"Execute": [
		OCString("command", ""),
		OCString("prompt", "")
		# TODO: startupnotify
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
		OCBoolean("linear", False)
		# TODO: finalactions
	],
}

#=====================================================================================
# Config parsing and interaction
#=====================================================================================

def create_empty_action():
	return xml.dom.minidom.parseString('<action name="Execute"></action>').documentElement

#-------------------------------------------------------------------------------------

class OBAction:
	def __init__(self, dom, parent):
		self.dom = dom
		self.parent = parent
		self.options = {}
		self.option_defs = []

		# parse 'name' attribute, get options hash and parse
		self.name = xml_parse_attr(dom, "name")
		self.parse()

	def parse(self):
		try:
			self.option_defs = actions[self.name]
		except KeyError:
			pass

		for od in self.option_defs:
			od.parse(self)

	def mutate(self, newtype):
		if actions[newtype] == self.option_defs:
			return

		xml_remove_all_children(self.dom)
		xml_set_attr(self.dom, "name", newtype)
		self.options = {}
		self.option_defs = []
		self.name = newtype
		self.parse()

#-------------------------------------------------------------------------------------

class OBKeyBind:
	def __init__(self, dom, parent=None):
		self.children = []
		self.actions = []
		self.parent = parent

		self.key = xml_parse_attr(dom, "key")
		self.chroot = xml_parse_attr_bool(dom, "chroot")
		self.dom = dom

		kbinds = xml_find_nodes(dom, "keybind")
		if len(kbinds):
			for k in kbinds:
				self.children.append(OBKeyBind(k))
		else:
			for a in xml_find_nodes(dom, "action"):
				self.actions.append(OBAction(a, self))

	def set_key(self, key):
		self.key = key
		xml_set_attr(self.dom, "key", key)

	def set_chroot(self, chroot):
		self.chroot = chroot
		if chroot:
			xml_set_attr(self.dom, "chroot", "true")
		else:
			xml_remove_attr(self.dom, "chroot")

	def insert_empty_action(self, after=None):
		newact = create_empty_action()

		if after:
			xml_insert_after(self.dom, newact, after.dom)
			oba = OBAction(newact, self)
			self.actions.insert(self.actions.index(after)+1, oba)
		else:
			xml_insert_after(self.dom, newact)
			oba = OBAction(newact, self)
			self.actions.append(oba)
		return oba

	def remove_action(self, action):
		xml_remove_child(self.dom, action.dom)
		self.actions.remove(action)

	def move_up(self, action):
		xml_move_up(self.dom, action.dom)
		i = self.actions.index(action)
		tmp = self.actions[i-1]
		self.actions[i-1] = action
		self.actions[i] = tmp

	def move_down(self, action):
		xml_move_down(self.dom, action.dom)
		i = self.actions.index(action)
		tmp = self.actions[i+1]
		self.actions[i+1] = action
		self.actions[i] = tmp


#-------------------------------------------------------------------------------------

class OBKeyboard:
	def __init__(self, dom):
		self.chainQuitKey = None
		self.chainQuitKey_xml = None
		self.keybinds = []

		cqk = xml_find_node(dom, "chainQuitKey")
		if cqk:
			self.chainQuitKey = xml_parse_string(cqk)
			self.chainQuitKey_xml = cqk

		for keybind in xml_find_nodes(dom, "keybind"):
			self.keybinds.append(OBKeyBind(keybind))

	def set_chainQuitKey(self, key):
		self.chainQuitKey = key
		xml_set_string(self.chainQuitKey_xml, key)

#-------------------------------------------------------------------------------------

class OpenboxConfig:
	def __init__(self):
		self.dom = None
		self.keyboard = None

	def load(self, path):
		# load config DOM
		self.dom = xml.dom.minidom.parse(path)

		# try load keyboard DOM
		keyboard = xml_find_node(self.dom.documentElement, "keyboard")
		if keyboard:
			self.keyboard = OBKeyboard(keyboard)


	def save(self, path):
		if self.dom is None:
			return

		with file(path, "w") as f:
			f.write(self.dom.toxml("utf-8"))

ob = OpenboxConfig()
ob.load("rc.xml")
