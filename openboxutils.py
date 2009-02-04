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
		for a in action.option_defs:
			self.add_row(a.name + ":", a.generate_widget(action))
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

		def editingstarted(cell, widget, path):
			widget.set_wrap_width(4)

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
			self.keybind.actions.remove(model.get_value(it, 1))
			isok = self.model.remove(it)
			if isok:
				self.view.get_selection().select_iter(it)

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
#def xml_set_string(elt, string):
#	elt.firstChild.nodeValue = string
#
#def xml_set_bool(elt, b):
#	if b:
#		xml_set_string(elt, "yes")
#	else:
#		xml_set_string(elt, "no")
#
#def xml_set_attr(elt, name, string):
#	elt.setAttribute(name, string)
#
#def xml_remove_attr(elt, name):
#	try:
#		elt.removeAttribute(name)
#	except xml.dom.NotFoundErr:
#		pass
#
#def xml_remove_child(elt, child):
#	c = elt.removeChild(child)
#	c.unlink()
#
#def xml_remove_all_children(elt):
#	last = elt.lastChild
#	while last:
#		xml_remove_child(elt, last)
#		last = elt.lastChild
#
#def xml_insert_after(elt, new, after=None):
#	if after:
#		elt.insertBefore(new, after.nextSibling)
#	else:
#		elt.appendChild(new)
#
#def xml_insert_textvalue_after(elt, text, value, after=None):
#	newdom = xml.dom.minidom.parseString("<{0}>{1}</{0}>".format(text, value)).documentElement
#	xml_insert_after(elt, newdom, after)
#	return newdom
#
#def xml_move_up(elt, what):
#	upper = what.previousSibling
#	tmp = elt.removeChild(what)
#	elt.insertBefore(tmp, upper)
#
#def xml_move_down(elt, what):
#	down = what.nextSibling
#	tmp = elt.removeChild(down)
#	elt.insertBefore(tmp, what)

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
		if not node:
			for a in self.alts:
				node = xml_find_node(dom, a)
				if node:
					break
		if node:
			action.options[self.name] = int(xml_parse_string(node))
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
		num.connect('changed', changed, action)
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
		OCBoolean("linear", False)
		# TODO: finalactions
	],
	"PreviousWindow": [
		OCBoolean("dialog", True),
		OCBoolean("bar", True),
		OCBoolean("raise", False),
		OCBoolean("allDesktops", False),
		OCBoolean("panels", False),
		OCBoolean("desktop", False),
		OCBoolean("linear", False)
		# TODO: finalactions
	],
	"DirectionalFocusNorth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalFocusSouth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalFocusEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalFocusWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalFocusNorthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalFocusNorthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalFocusSouthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalFocusSouthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetNorth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetSouth": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetNorthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetNorthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetSouthEast": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
	"DirectionalTargetSouthWest": [ OCBoolean("dialog", True), OCBoolean("bar", True), OCBoolean("raise", False) ], # TODO: finalactions
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
}

#=====================================================================================
# Config parsing and interaction
#=====================================================================================

class OBAction:
	def __init__(self, parent):
		self.parent = parent
		self.options = {}
		self.option_defs = []

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
		self.parent = parent
		self.key = None
		self.chroot = False

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
				newa = OBAction(self)
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
		newact = OBAction(self)
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

		for k in self.keybinds:
			root.appendChild(k.deparse())

		return root

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
