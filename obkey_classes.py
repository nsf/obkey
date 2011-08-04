#!/usr/bin/python
#------------------------------------------------------------------------------
# Openbox Key Editor
# Copyright (C) 2009 nsf <no.smile.face@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#------------------------------------------------------------------------------

import xml.dom.minidom
from StringIO import StringIO
from string import strip
import gobject
import copy
import gtk
import sys
import os
import gettext

#=====================================================================================
# Config
#=====================================================================================

# XXX: Sorry, for now this is it. If you know a better way to do this with setup.py:
# please mail me.

config_prefix = '/usr'
config_icons = os.path.join(config_prefix, 'share/obkey/icons')
config_locale_dir = os.path.join(config_prefix, 'share/locale')

gettext.install('obkey', config_locale_dir) # init gettext

# localized title
config_title = _('obkey')

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
	try:
		toksgdk = [replace_table_openbox2gtk[mod.lower()] for mod in toks[:-1]]
	except:
		return (0, 0)
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
# This is the uber cool switchers/conditions(sensors) system.
# Helps a lot with widgets sensitivity.
#=====================================================================================

class SensCondition:
	def __init__(self, initial_state):
		self.switchers = []
		self.state = initial_state

	def register_switcher(self, sw):
		self.switchers.append(sw)

	def set_state(self, state):
		if self.state == state:
			return
		self.state = state
		for sw in self.switchers:
			sw.notify()

class SensSwitcher:
	def __init__(self, conditions):
		self.conditions = conditions
		self.widgets = []

		for c in conditions:
			c.register_switcher(self)

	def append(self, widget):
		self.widgets.append(widget)

	def set_sensitive(self, state):
		for w in self.widgets:
			w.set_sensitive(state)

	def notify(self):
		for c in self.conditions:
			if not c.state:
				self.set_sensitive(False)
				return
		self.set_sensitive(True)

#=====================================================================================
# KeyTable
#=====================================================================================

class KeyTable:
	def __init__(self, actionlist, ob):
		self.widget = gtk.VBox()
		self.ob = ob
		self.actionlist = actionlist
		actionlist.set_callback(self.actions_cb)

		self.icons = self.load_icons()

		self.model, self.cqk_model = self.create_models()
		self.view, self.cqk_view = self.create_views(self.model, self.cqk_model)

		# copy & paste
		self.copied = None

		# sensitivity switchers & conditions
		self.cond_insert_child = SensCondition(False)
		self.cond_paste_buffer = SensCondition(False)
		self.cond_selection_available = SensCondition(False)

		self.sw_insert_child_and_paste = SensSwitcher([self.cond_insert_child, self.cond_paste_buffer])
		self.sw_insert_child = SensSwitcher([self.cond_insert_child])
		self.sw_paste_buffer = SensSwitcher([self.cond_paste_buffer])
		self.sw_selection_available = SensSwitcher([self.cond_selection_available])

		# self.context_menu
		self.context_menu = self.create_context_menu()

		for kb in self.ob.keyboard.keybinds:
			self.apply_keybind(kb)

		self.apply_cqk_initial_value()

		# self.add_child_button
		self.widget.pack_start(self.create_toolbar(), False)
		self.widget.pack_start(self.create_scroll(self.view))
		self.widget.pack_start(self.create_cqk_hbox(self.cqk_view), False)

		if len(self.model):
			self.view.get_selection().select_iter(self.model.get_iter_first())

		self.sw_insert_child_and_paste.notify()
		self.sw_insert_child.notify()
		self.sw_paste_buffer.notify()
		self.sw_selection_available.notify()

	def create_cqk_hbox(self, cqk_view):
		cqk_hbox = gtk.HBox()
		cqk_label = gtk.Label(_("chainQuitKey:"))
		cqk_label.set_padding(5,5)

		cqk_frame = gtk.Frame()
		cqk_frame.add(cqk_view)

		cqk_hbox.pack_start(cqk_label, False)
		cqk_hbox.pack_start(cqk_frame)
		return cqk_hbox

	def create_context_menu(self):
		context_menu = gtk.Menu()
		self.context_items = {}

		item = gtk.ImageMenuItem(gtk.STOCK_CUT)
		item.connect('activate', lambda menu: self.cut_selected())
		item.get_child().set_label(_("Cu_t"))
		context_menu.append(item)
		self.sw_selection_available.append(item)

		item = gtk.ImageMenuItem(gtk.STOCK_COPY)
		item.connect('activate', lambda menu: self.copy_selected())
		item.get_child().set_label(_("_Copy"))
		context_menu.append(item)
		self.sw_selection_available.append(item)

		item = gtk.ImageMenuItem(gtk.STOCK_PASTE)
		item.connect('activate', lambda menu: self.insert_sibling(self.copied))
		item.get_child().set_label(_("_Paste"))
		context_menu.append(item)
		self.sw_paste_buffer.append(item)

		item = gtk.ImageMenuItem(gtk.STOCK_PASTE)
		item.get_child().set_label(_("P_aste as child"))
		item.connect('activate', lambda menu: self.insert_child(self.copied))
		context_menu.append(item)
		self.sw_insert_child_and_paste.append(item)

		item = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
		item.connect('activate', lambda menu: self.del_selected())
		item.get_child().set_label(_("_Remove"))
		context_menu.append(item)
		self.sw_selection_available.append(item)

		context_menu.show_all()
		return context_menu

	def create_models(self):
		model = gtk.TreeStore(gobject.TYPE_UINT, # accel key
					gobject.TYPE_INT, # accel mods
					gobject.TYPE_STRING, # accel string (openbox)
					gobject.TYPE_BOOLEAN, # chroot
					gobject.TYPE_BOOLEAN, # show chroot
					gobject.TYPE_PYOBJECT # OBKeyBind
					)

		cqk_model = gtk.ListStore(gobject.TYPE_UINT, # accel key
					gobject.TYPE_INT, # accel mods
					gobject.TYPE_STRING) # accel string (openbox)
		return (model, cqk_model)

	def create_scroll(self, view):
		scroll = gtk.ScrolledWindow()
		scroll.add(view)
		scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		scroll.set_shadow_type(gtk.SHADOW_IN)
		return scroll

	def create_views(self, model, cqk_model):
		r0 = gtk.CellRendererAccel()
		r0.props.editable = True
		r0.connect('accel-edited', self.accel_edited)

		r1 = gtk.CellRendererText()
		r1.props.editable = True
		r1.connect('edited', self.key_edited)

		r2 = gtk.CellRendererToggle()
		r2.connect('toggled', self.chroot_toggled)

		c0 = gtk.TreeViewColumn(_("Key"), r0, accel_key=0, accel_mods=1)
		c1 = gtk.TreeViewColumn(_("Key (text)"), r1, text=2)
		c2 = gtk.TreeViewColumn(_("Chroot"), r2, active=3, visible=4)

		c0.set_expand(True)

		view = gtk.TreeView(model)
		view.append_column(c0)
		view.append_column(c1)
		view.append_column(c2)
		view.get_selection().connect('changed', self.view_cursor_changed)
		view.connect('button-press-event', self.view_button_clicked)

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

		cqk_view = gtk.TreeView(cqk_model)
		cqk_view.set_headers_visible(False)
		cqk_view.append_column(c0)
		cqk_view.append_column(c1)
		cqk_view.connect('focus-out-event', cqk_view_focus_lost)
		return (view, cqk_view)

	def create_toolbar(self):
		toolbar = gtk.Toolbar()
		toolbar.set_style(gtk.TOOLBAR_ICONS)
		toolbar.set_show_arrow(False)

		but = gtk.ToolButton(gtk.STOCK_SAVE)
		but.set_tooltip_text(_("Save ") + self.ob.path + _(" file"))
		but.connect('clicked', lambda but: self.ob.save())
		toolbar.insert(but, -1)

		toolbar.insert(gtk.SeparatorToolItem(), -1)

		but = gtk.ToolButton(self.icons['add_sibling'])
		but.set_tooltip_text(_("Insert sibling keybind"))
		but.connect('clicked', lambda but: self.insert_sibling(OBKeyBind()))
		toolbar.insert(but, -1)

		but = gtk.ToolButton(self.icons['add_child'])
		but.set_tooltip_text(_("Insert child keybind"))
		but.connect('clicked', lambda but: self.insert_child(OBKeyBind()))
		toolbar.insert(but, -1)
		self.sw_insert_child.append(but)

		but = gtk.ToolButton(gtk.STOCK_REMOVE)
		but.set_tooltip_text(_("Remove keybind"))
		but.connect('clicked', lambda but: self.del_selected())
		toolbar.insert(but, -1)
		self.sw_selection_available.append(but)

		sep = gtk.SeparatorToolItem()
		sep.set_draw(False)
		sep.set_expand(True)
		toolbar.insert(sep, -1)

		toolbar.insert(gtk.SeparatorToolItem(), -1)

		but = gtk.ToolButton(gtk.STOCK_QUIT)
		but.set_tooltip_text(_("Quit application"))
		but.connect('clicked', lambda but: gtk.main_quit())
		toolbar.insert(but, -1)
		return toolbar

	def apply_cqk_initial_value(self):
		cqk_accel_key, cqk_accel_mods = key_openbox2gtk(self.ob.keyboard.chainQuitKey)
		if cqk_accel_mods == 0:
			self.ob.keyboard.chainQuitKey = ""
		self.cqk_model.append((cqk_accel_key, cqk_accel_mods, self.ob.keyboard.chainQuitKey))

	def apply_keybind(self, kb, parent=None):
		accel_key, accel_mods = key_openbox2gtk(kb.key)
		chroot = kb.chroot
		show_chroot = len(kb.children) > 0 or not len(kb.actions)

		n = self.model.append(parent,
				(accel_key, accel_mods, kb.key, chroot, show_chroot, kb))

		for c in kb.children:
			self.apply_keybind(c, n)

	def load_icons(self):
		icons = {}
		icons_path = 'icons'
		if os.path.isdir(config_icons):
			icons_path = config_icons
		icons['add_sibling'] = gtk.image_new_from_file(os.path.join(icons_path, "add_sibling.png"))
		icons['add_child'] = gtk.image_new_from_file(os.path.join(icons_path, "add_child.png"))
		return icons


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
			else:
				view.grab_focus()
				view.get_selection().unselect_all()
				self.context_menu.popup(None, None, None, event.button, time)
			return 1

	def actions_cb(self):
		(model, it) = self.view.get_selection().get_selected()
		kb = model.get_value(it, 5)
		if len(kb.actions) == 0:
			model.set_value(it, 4, True)
			self.cond_insert_child.set_state(True)
		else:
			model.set_value(it, 4, False)
			self.cond_insert_child.set_state(False)

	def view_cursor_changed(self, selection):
		(model, it) = selection.get_selected()
		actions = None
		if it:
			kb = model.get_value(it, 5)
			if len(kb.children) == 0 and not kb.chroot:
				actions = kb.actions
			self.cond_selection_available.set_state(True)
			self.cond_insert_child.set_state(len(kb.actions) == 0)
		else:
			self.cond_insert_child.set_state(False)
			self.cond_selection_available.set_state(False)
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
		elif not kb.children:
			self.actionlist.set_actions(kb.actions)

	#-----------------------------------------------------------------------------
	def cut_selected(self):
		self.copy_selected()
		self.del_selected()

	def copy_selected(self):
		(model, it) = self.view.get_selection().get_selected()
		if it:
			sel = model.get_value(it, 5)
			self.copied = copy.deepcopy(sel)
			self.cond_paste_buffer.set_state(True)

	def _insert_keybind(self, keybind, parent=None, after=None):
		keybind.parent = parent
		if parent:
			kbs = parent.children
		else:
			kbs = self.ob.keyboard.keybinds

		if after:
			kbs.insert(kbs.index(after)+1, keybind)
		else:
			kbs.append(keybind)

	def insert_sibling(self, keybind):
		(model, it) = self.view.get_selection().get_selected()

		accel_key, accel_mods = key_openbox2gtk(keybind.key)
		show_chroot = len(keybind.children) > 0 or not len(keybind.actions)

		if it:
			parent_it = model.iter_parent(it)
			parent = None
			if parent_it:
				parent = model.get_value(parent_it, 5)
			after = model.get_value(it, 5)

			self._insert_keybind(keybind, parent, after)
			newit = self.model.insert_after(parent_it, it,
					(accel_key, accel_mods, keybind.key, keybind.chroot, show_chroot, keybind))
		else:
			self._insert_keybind(keybind)
			newit = self.model.append(None,
					(accel_key, accel_mods, keybind.key, keybind.chroot, show_chroot, keybind))

		if newit:
			for c in keybind.children:
				self.apply_keybind(c, newit)
			self.view.get_selection().select_iter(newit)

	def insert_child(self, keybind):
		(model, it) = self.view.get_selection().get_selected()
		parent = model.get_value(it, 5)
		self._insert_keybind(keybind, parent)

		accel_key, accel_mods = key_openbox2gtk(keybind.key)
		show_chroot = len(keybind.children) > 0 or not len(keybind.actions)

		newit = self.model.append(it,
				(accel_key, accel_mods, keybind.key, keybind.chroot, show_chroot, keybind))

		# it means that we have inserted first child here, change status
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
		label = gtk.Label(_(label_text))
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

		# copy & paste buffer
		self.copied = None

		# sensitivity switchers & conditions
		self.cond_paste_buffer = SensCondition(False)
		self.cond_selection_available = SensCondition(False)
		self.cond_action_list_nonempty = SensCondition(False)
		self.cond_can_move_up = SensCondition(False)
		self.cond_can_move_down = SensCondition(False)

		self.sw_paste_buffer = SensSwitcher([self.cond_paste_buffer])
		self.sw_selection_available = SensSwitcher([self.cond_selection_available])
		self.sw_action_list_nonempty = SensSwitcher([self.cond_action_list_nonempty])
		self.sw_can_move_up = SensSwitcher([self.cond_can_move_up])
		self.sw_can_move_down = SensSwitcher([self.cond_can_move_down])

		self.model = self.create_model()
		self.view = self.create_view(self.model)

		self.context_menu = self.create_context_menu()

		self.widget.pack_start(self.create_scroll(self.view))
		self.widget.pack_start(self.create_toolbar(), False)

		self.sw_paste_buffer.notify()
		self.sw_selection_available.notify()
		self.sw_action_list_nonempty.notify()
		self.sw_can_move_up.notify()
		self.sw_can_move_down.notify()

	def create_model(self):
		return gtk.ListStore(gobject.TYPE_STRING, # name of the action
					gobject.TYPE_PYOBJECT) # associated OBAction

	def create_choices(self):
		choices = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
		action_list = {}
		for a in actions:
			action_list[_(a)] = a
		for a in sorted(action_list.keys()):
			choices.append((a,action_list[a]))
		return choices

	def create_scroll(self, view):
		scroll = gtk.ScrolledWindow()
		scroll.add(view)
		scroll.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		scroll.set_shadow_type(gtk.SHADOW_IN)
		return scroll

	def create_view(self, model):
		renderer = gtk.CellRendererCombo()

		def editingstarted(cell, widget, path):
			widget.set_wrap_width(4)

		renderer.props.model = self.create_choices()
		renderer.props.text_column = 0
		renderer.props.editable = True
		renderer.props.has_entry = False
		renderer.connect('changed', self.action_class_changed)
		renderer.connect('editing-started', editingstarted)

		column = gtk.TreeViewColumn(_("Actions"), renderer, text=0)

		view = gtk.TreeView(model)
		view.append_column(column)
		view.get_selection().connect('changed', self.view_cursor_changed)
		view.connect('button-press-event', self.view_button_clicked)
		return view

	def create_context_menu(self):
		context_menu = gtk.Menu()
		self.context_items = {}

		item = gtk.ImageMenuItem(gtk.STOCK_CUT)
		item.connect('activate', lambda menu: self.cut_selected())
		item.get_child().set_label(_("Cu_t"))
		context_menu.append(item)
		self.sw_selection_available.append(item)

		item = gtk.ImageMenuItem(gtk.STOCK_COPY)
		item.connect('activate', lambda menu: self.copy_selected())
		item.get_child().set_label(_("_Copy"))
		context_menu.append(item)
		self.sw_selection_available.append(item)

		item = gtk.ImageMenuItem(gtk.STOCK_PASTE)
		item.connect('activate', lambda menu: self.insert_action(self.copied))
		item.get_child().set_label(_("_Paste"))
		context_menu.append(item)
		self.sw_paste_buffer.append(item)

		item = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
		item.connect('activate', lambda menu: self.del_selected())
		item.get_child().set_label(_("_Remove"))
		context_menu.append(item)
		self.sw_selection_available.append(item)

		context_menu.show_all()
		return context_menu

	def create_toolbar(self):
		toolbar = gtk.Toolbar()
		toolbar.set_style(gtk.TOOLBAR_ICONS)
		toolbar.set_icon_size(gtk.ICON_SIZE_SMALL_TOOLBAR)
		toolbar.set_show_arrow(False)

		but = gtk.ToolButton(gtk.STOCK_ADD)
		but.set_tooltip_text(_("Insert action"))
		but.connect('clicked', lambda but: self.insert_action(OBAction("Focus")))
		toolbar.insert(but, -1)

		but = gtk.ToolButton(gtk.STOCK_REMOVE)
		but.set_tooltip_text(_("Remove action"))
		but.connect('clicked', lambda but: self.del_selected())
		toolbar.insert(but, -1)
		self.sw_selection_available.append(but)

		but = gtk.ToolButton(gtk.STOCK_GO_UP)
		but.set_tooltip_text(_("Move action up"))
		but.connect('clicked', lambda but: self.move_selected_up())
		toolbar.insert(but, -1)
		self.sw_can_move_up.append(but)

		but = gtk.ToolButton(gtk.STOCK_GO_DOWN)
		but.set_tooltip_text(_("Move action down"))
		but.connect('clicked', lambda but: self.move_selected_down())
		toolbar.insert(but, -1)
		self.sw_can_move_down.append(but)

		sep = gtk.SeparatorToolItem()
		sep.set_draw(False)
		sep.set_expand(True)
		toolbar.insert(sep, -1)

		but = gtk.ToolButton(gtk.STOCK_DELETE)
		but.set_tooltip_text(_("Remove all actions"))
		but.connect('clicked', lambda but: self.clear())
		toolbar.insert(but, -1)
		self.sw_action_list_nonempty.append(but)
		return toolbar
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
			else:
				view.grab_focus()
				view.get_selection().unselect_all()
				self.context_menu.popup(None, None, None, event.button, time)
			return 1

	def action_class_changed(self, combo, path, it):
		m = combo.props.model
		ntype = m.get_value(it, 1)
		self.model[path][0] = m.get_value(it, 0)
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
		if act:
			l = len(self.actions)
			i = self.actions.index(act)
			self.cond_can_move_up.set_state(i != 0)
			self.cond_can_move_down.set_state(l > 1 and i+1 < l)
			self.cond_selection_available.set_state(True)
		else:
			self.cond_can_move_up.set_state(False)
			self.cond_can_move_down.set_state(False)
			self.cond_selection_available.set_state(False)

	#-----------------------------------------------------------------------------
	def cut_selected(self):
		self.copy_selected()
		self.del_selected()

	def copy_selected(self):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if it:
			a = model.get_value(it, 1)
			self.copied = copy.deepcopy(a)
			self.cond_paste_buffer.set_state(True)

	def clear(self):
		if self.actions is None or not len(self.actions):
			return

		del self.actions[:]
		self.model.clear()

		self.cond_action_list_nonempty.set_state(False)
		if self.actions_cb:
			self.actions_cb()

	def move_selected_up(self):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if not it:
			return

		i, = self.model.get_path(it)
		l = len(self.model)
		self.cond_can_move_up.set_state(i-1 != 0)
		self.cond_can_move_down.set_state(l > 1 and i < l)
		if i == 0:
			return

		itprev = self.model.get_iter(i-1)
		self.model.swap(it, itprev)
		action = self.model.get_value(it, 1)

		i = self.actions.index(action)
		tmp = self.actions[i-1]
		self.actions[i-1] = action
		self.actions[i] = tmp

	def move_selected_down(self):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if not it:
			return

		i, = self.model.get_path(it)
		l = len(self.model)
		self.cond_can_move_up.set_state(i+1 != 0)
		self.cond_can_move_down.set_state(l > 1 and i+2 < l)
		if i+1 >= l:
			return

		itnext = self.model.iter_next(it)
		self.model.swap(it, itnext)
		action = self.model.get_value(it, 1)

		i = self.actions.index(action)
		tmp = self.actions[i+1]
		self.actions[i+1] = action
		self.actions[i] = tmp

	def insert_action(self, action):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if it:
			self._insert_action(action, model.get_value(it, 1))
			newit = self.model.insert_after(it, (_(action.name), action))
		else:
			self._insert_action(action)
			newit = self.model.append((_(action.name), action))

		if newit:
			self.view.get_selection().select_iter(newit)

		self.cond_action_list_nonempty.set_state(len(self.model))
		if self.actions_cb:
			self.actions_cb()

	def del_selected(self):
		if self.actions is None:
			return

		(model, it) = self.view.get_selection().get_selected()
		if it:
			self.actions.remove(model.get_value(it, 1))
			isok = self.model.remove(it)
			if isok:
				self.view.get_selection().select_iter(it)

		self.cond_action_list_nonempty.set_state(len(self.model))
		if self.actions_cb:
			self.actions_cb()

	#-----------------------------------------------------------------------------

	def set_actions(self, actionlist):
		self.actions = actionlist
		self.model.clear()
		self.widget.set_sensitive(self.actions is not None)
		if not self.actions:
			return
		for a in self.actions:
			self.model.append((_(a.name), a))
		if len(self.model):
			self.view.get_selection().select_iter(self.model.get_iter_first())
		self.cond_action_list_nonempty.set_state(len(self.model))

	def _insert_action(self, action, after=None):
		if after:
			self.actions.insert(self.actions.index(after)+1, action)
		else:
			self.actions.append(action)

	def set_callback(self, cb):
		self.actions_cb = cb

#=====================================================================================
# MiniActionList
#=====================================================================================

class MiniActionList(ActionList):
	def __init__(self, proptable=None):
		ActionList.__init__(self, proptable)
		self.widget.set_size_request(-1, 120)
		self.view.set_headers_visible(False)

	def create_choices(self):
		choices = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
		action_list = {}
		for a in actions:
			action_list[_(a)] = a
		for a in sorted(action_list.keys()):
			if len(actions[action_list[a]]) == 0:
				choices.append((a,action_list[a]))
		return choices

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
	if elt.hasChildNodes():
		return elt.firstChild.nodeValue
	else:
		return ""

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

def fixed_writexml(self, writer, indent="", addindent="", newl=""):
	# indent = current indentation
	# addindent = indentation to add to higher levels
	# newl = newline string
	writer.write(indent+"<" + self.tagName)

	attrs = self._get_attributes()
	a_names = attrs.keys()
	a_names.sort()

	for a_name in a_names:
		writer.write(" %s=\"" % a_name)
		xml.dom.minidom._write_data(writer, attrs[a_name].value)
		writer.write("\"")
	if self.childNodes:
		if len(self.childNodes) == 1 \
		and self.childNodes[0].nodeType == xml.dom.minidom.Node.TEXT_NODE:
			writer.write(">")
			self.childNodes[0].writexml(writer, "", "", "")
			writer.write("</%s>%s" % (self.tagName, newl))
			return
		writer.write(">%s" % newl)
		for node in self.childNodes:
			fixed_writexml(node, writer,indent+addindent,addindent,newl)
		writer.write("%s</%s>%s" % (indent,self.tagName,newl))
	else:
		writer.write("/>%s"%(newl))

def fixed_toprettyxml(self, indent="", addindent="\t", newl="\n"):
	# indent = current indentation
	# addindent = indentation to add to higher levels
	# newl = newline string
	writer = StringIO()

	fixed_writexml(self, writer, indent, addindent, newl)
	return writer.getvalue()

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
		return xml.dom.minidom.parseString("<"+str(self.name)+">"+str(val)+"</"+str(self.name)+">").documentElement

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
		if node:
			action.options[self.name] = xml_parse_string(node)
		else:
			action.options[self.name] = self.default

	def deparse(self, action):
		val = action.options[self.name]
		if val == self.default:
			return None
		return xml.dom.minidom.parseString("<"+str(self.name)+">"+str(val)+"</"+str(self.name)+">").documentElement

	def generate_widget(self, action):
		def changed(combo, action):
			text = combo.get_active()
			action.options[self.name] = self.choices[text]

		model = gtk.ListStore(gobject.TYPE_STRING)
		for c in self.choices:
			model.append((_(c),))

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
		return xml.dom.minidom.parseString("<"+str(self.name)+">"+str(val)+"</"+str(self.name)+">").documentElement

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
			return xml.dom.minidom.parseString("<"+str(self.name)+">yes</"+str(self.name)+">").documentElement
		else:
			return xml.dom.minidom.parseString("<"+str(self.name)+">no</"+str(self.name)+">").documentElement

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
			root.appendChild(xml.dom.minidom.parseString("<wmclass>"+action.options['startupnotify_wmclass']+"</wmclass>").documentElement)
		if action.options['startupnotify_name'] != "":
			root.appendChild(xml.dom.minidom.parseString("<name>"+action.options['startupnotify_name']+"</name>").documentElement)
		if action.options['startupnotify_icon'] != "":
			root.appendChild(xml.dom.minidom.parseString("<icon>"+action.options['startupnotify_icon']+"</icon>").documentElement)
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
			label = gtk.Label(_(label_text))
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
	def __init__(self, name=None):
		self.options = {}
		self.option_defs = []
		self.name = name
		if name:
			self.mutate(name)

	def parse(self, dom):
		# call parseChild if childNodes exist
		if dom.hasChildNodes():
			for child in dom.childNodes:
				self.parseChild(child)

		# parse 'name' attribute, get options hash and parse
		self.name = xml_parse_attr(dom, "name")

		try:
			self.option_defs = actions[self.name]
		except KeyError:
			pass

		for od in self.option_defs:
			od.parse(self, dom)

	# calls itself until no childNodes are found and strip() values of last node
	def parseChild(self, dom):
		try:
			if dom.hasChildNodes():
				for child in dom.childNodes:
					try:
						child.nodeValue = child.nodeValue.strip()
					except AttributeError:
						pass
					self.parseChild(child)
		except AttributeError:
			pass
		else:
			try:
				dom.nodeValue = dom.nodeValue.strip()
			except AttributeError:
				pass

	def deparse(self):
		root = xml.dom.minidom.parseString('<action name="'+str(self.name)+'"/>').documentElement
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

	def __deepcopy__(self, memo):
		# we need deepcopy here, because option_defs are never copied
		result = self.__class__()
		result.option_defs = self.option_defs
		result.options = copy.deepcopy(self.options, memo)
		result.name = copy.deepcopy(self.name, memo)
		return result
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
			root = xml.dom.minidom.parseString('<keybind key="'+str(self.key)+'" chroot="yes"/>').documentElement
		else:
			root = xml.dom.minidom.parseString('<keybind key="'+str(self.key)+'"/>').documentElement

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
		chainQuitKey_node = xml.dom.minidom.parseString('<chainQuitKey>'+str(self.chainQuitKey)+'</chainQuitKey>').documentElement
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
		newdom = xml_find_node(xml.dom.minidom.parseString(fixed_toprettyxml(self.keyboard.deparse(),"  ","  ")),"keyboard")
		self.dom.documentElement.replaceChild(newdom, keyboard)
		f = file(self.path, "w")
		if f:
			xmlform = self.dom.documentElement
			f.write(xmlform.toxml("utf8"))
			f.close()
		self.reconfigure_openbox()

	def reconfigure_openbox(self):
		os.system("openbox --reconfigure")
