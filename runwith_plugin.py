#!/usr/bin/env python2

"""runwith-plugin.py - Terminator Plugin to run arbitrary commands on arbitrary text"""
import subprocess
from gi.repository import Gtk, GObject, Pango, Gdk
import terminatorlib.plugin as plugin
import re
from terminatorlib import config
from terminatorlib.translation import _
import terminatorlib.terminator
from terminatorlib.util import dbg
from terminatorlib.borg import Borg

# Every plugin you want Terminator to load *must* be listed in 'AVAILABLE'
AVAILABLE = [ 'RunWithNg' ]

class RunWithNg(plugin.PluginNg):

    """Handle custom arbitrary regexes"""
    capabilities = ['plugin_ng']
    plugin_name = 'RunWithNg'

    def __init__(self):
        self.read_config()
        # replicate matches across all terminals
        plugin.PluginNg.__init__(self)

    def read_config(self):

        self.config = {}
        conf = config.Config()

        saved_config = conf.plugin_get_config(self.plugin_name)

        if saved_config:
            for key in saved_config:

                s = saved_config[key]

                if not ( s.has_key('pattern') and
                         s.has_key('name') and
                         s.has_key('actions') and
                         len(s['actions']) > 0 ):
                    continue

                if not self.config.has_key(key):
                    self.config[key] = {}

                self.config[key]['enabled'] = s.as_bool('enabled')
                self.config[key]['name'] = s['name']
                self.config[key]['pattern'] = s['pattern']
                self.config[key]['compiled'] = re.compile(self.config[key]['pattern'])
                self.config[key]['actions'] = s['actions']

                for action in s['actions'].keys():
                    if s['actions'][action].has_key('in-terminal'):
                        self.config[key]['actions'][action]['in-terminal'] = s['actions'][action].as_bool('in-terminal')
                    else:
                        # default value
                        self.config[key]['actions'][action]['in-terminal'] = True

                    if s['actions'][action].has_key('use-shell'):
                        self.config[key]['actions'][action]['use-shell'] = s['actions'][action].as_bool('use-shell')
                    else:
                        # default value
                        self.config[key]['actions'][action]['use-shell'] = False

    # Return a key/value dictionary of all matches the plugin wants to register
    def callback_get_matches(self):
        return {key: value['pattern'] for key, value in self.config.items() if self.config[key]['enabled'] == True}

    # Not implemented, not necessary here
    #def callback_nameopen(self, matched_text, match_key):

    # Not implemented, not necessary
    #def callback_open_transform(self, matched_text, match_key):

    # Add our own entries to the popup menu, depending on the current match
    def callback_popup_menu(self, menuitems, terminal, matched_text, match_key):

        # selected_text = None
        #if terminal.vte.get_has_selection():
        #    # Madness!
        #    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        #    saved_clipboard_text = clipboard.request_text(lambda c, t, d: None, None)
        #    terminal.vte.copy_clipboard_format(Vte.Format.TEXT)
        #    selected_text = clipboard.request_text(lambda c, t, d: None, None)
        #    clipboard.set_text(saved_clipboard_text, -1)


        # Top level entry, expands to our own submenu
        if matched_text != None and match_key != None:
            run_with_item = Gtk.MenuItem.new_with_mnemonic(('%s: ' % self.config[match_key]['name']) + _('_Run With'))
        else:
            run_with_item = Gtk.MenuItem.new_with_mnemonic(_('_Run With'))

        menuitems.append(run_with_item)


        # actual submenu
        run_with_submenu = Gtk.Menu()
        run_with_item.set_submenu(run_with_submenu)

        # Preferences item is shown regardless of whether there's a match
        menuitem = Gtk.SeparatorMenuItem()
        run_with_submenu.append(menuitem)
        menuitem = Gtk.MenuItem.new_with_mnemonic(_('_Preferences'))
        menuitem.connect("activate", self.configure)
        run_with_submenu.append(menuitem)

        if len(self.config) == 0:
            return

        if (match_key == None or matched_text == None):
            return

        dbg('Creating RunWith submenu for match %s, text %s' % (match_key, matched_text))

        theme = Gtk.IconTheme.get_default()

        for action in self.config[match_key]['actions'].keys():
            real_action = list(self.config[match_key]['actions'][action]['command'])

            if str.find(self.config[match_key]['pattern'], '@builtin%') != 0:
                for i, word in enumerate(real_action):
                    real_action[i] = self.config[match_key]['compiled'].sub(real_action[i], matched_text)
            else:
                # for builtin matches, we don't have the actual RE available in the config
                for i, word in enumerate(real_action):
                    real_action[i] = re.sub('\\\g<0>', matched_text, real_action[i])

            exe = real_action[0]
            iconinfo = theme.choose_icon([exe], Gtk.IconSize.MENU, Gtk.IconLookupFlags.USE_BUILTIN)

            if iconinfo:
                image = Gtk.Image()
                image.set_from_icon_name(exe, Gtk.IconSize.MENU)
                menuitem = Gtk.ImageMenuItem(' '.join(real_action))
                menuitem.set_image(image)
            else:
                menuitem = Gtk.MenuItem(' '.join(real_action))

            run_with_submenu.prepend(menuitem)

            terminals = terminal.terminator.get_target_terms(terminal)

            in_terminal = self.config[match_key]['actions'][action]['in-terminal']
            use_shell = self.config[match_key]['actions'][action]['use-shell']

            menuitem.connect("activate", self.run_command, {'terminals' : terminals, 'command' : real_action, 'in-terminal': in_terminal, 'use-shell': use_shell})

    def run_command(self, widget, cmd_info):

        dbg('Running command with info: %s' % cmd_info)

        if cmd_info['in-terminal'] == True:
            for terminal in cmd_info['terminals']:
                command = ' '.join(cmd_info['command']) + '\n'
                terminal.vte.feed_child(command, len(command))
        else:
            popen = subprocess.Popen(cmd_info['command'], shell = cmd_info['use-shell'], stdin = None, stdout = None, stderr = None, close_fds = True)
            dbg("Running %s, pid %s" % (cmd_info['command'], popen.pid))

    '''
    # Sample config snippet
    [[[1]]]
      name = bar
      pattern = (?P<NAME>b.r)
      enabled = True
      [[[[actions]]]]
        [[[[[1]]]]]
          command = mousepad, \g<NAME>
          in-terminal = False
        [[[[[2]]]]]
          command = vim, \g<NAME>
          in-terminal = True

    [[[2]]]
      name = baz
      pattern = (?P<WORD>baz)
      enabled = True
      [[[[actions]]]]
        [[[[[1]]]]]
          command = mousepad, \g<WORD>
    [[[3]]]
      name = foobar
      enabled = True
      pattern = fo(?P<WORD>ob)ar
      [[[[actions]]]]
        [[[[[1]]]]]
          command = ls, \g<WORD>
    '''

    # GUI configuration for the plugin. Same thing can also be
    # done by manually editing the configuration file, of course.
    # This uses GTK+ TreeViews.
    def configure(self, widget):

        store_factory = StoreFactory()
        gen_store = store_factory.create_gen_store(self.config)

        action_stores = {}
        for pattern in self.config.keys():
            action_stores[pattern] = store_factory.create_action_store(self.config[pattern]['actions'])

        dialog = RunWithDialog(gen_store, action_stores, widget, title = 'RunWith configuration')

        icon_theme = Gtk.IconTheme.get_default()
        if icon_theme.lookup_icon('terminator-run-with', 48, 0):
            dialog.set_icon_name('terminator-run-with')
        else:
            dbg('Cannot load Terminator RunWith icon')
            icon = dialog.render_icon(Gtk.STOCK_DIALOG_INFO, Gtk.IconSize.BUTTON)
            dialog.set_icon(icon)

        while True:
            result = dialog.run()
            if result == Gtk.ResponseType.OK:
                if dialog.is_gen_store_valid():
                    self.save_config(dialog)
                    break
            else:
                break

        dialog.destroy()
        return

    def save_config(self, dialog):

        terminator = terminatorlib.terminator.Terminator()
        for terminal in terminator.terminals:
            terminal.pluginng_matches_add(self)

        self.config = {}

        conf = config.Config()
        conf.plugin_del_config(self.plugin_name)

        gen_store = dialog.gen_store
        action_stores = dialog.action_stores

        for pattern_row in gen_store:
            pkey, enabled, name, pattern = dialog.get_gen_fields(pattern_row)

            self.config[pkey] = {}
            self.config[pkey]['enabled'] = enabled
            self.config[pkey]['name'] = name
            self.config[pkey]['pattern'] = pattern

            self.config[pkey]['actions'] = {}
            for action_row in action_stores[pkey]:
                ckey, command, in_terminal, use_shell = dialog.get_action_fields(action_row)
                self.config[pkey]['actions'][ckey] = {}
                self.config[pkey]['actions'][ckey]['command'] = command
                self.config[pkey]['actions'][ckey]['in-terminal'] = in_terminal
                self.config[pkey]['actions'][ckey]['use-shell'] = use_shell

            conf.plugin_set(self.plugin_name, pkey, self.config[pkey])

        conf.save()

        # we don't want to save compiled REs
        for pkey in self.config.keys():
            self.config[pkey]['compiled'] = re.compile(self.config[pkey]['pattern'])

        # Update terminal config
        for terminal in terminator.terminals:
            terminal.pluginng_matches_add(self)

class RunWithDialog(Gtk.Dialog):

    (M_COL_KEY, M_COL_ENABLED, M_COL_NAME, M_COL_PATTERN) = range(0, 4)
    (V_COL_ENABLED, V_COL_NAME, V_COL_PATTERN, V_COL_ACTIONS) = range(0, 4)

    (AM_COL_KEY, AM_COL_COMMAND, AM_COL_COMMANDL, AM_COL_IN_TERMINAL, AM_COL_USE_SHELL) = range(0, 5)

    def __init__(self, gen_store, action_stores, parent, title = 'Dialog'):

        Gtk.Dialog.__init__(self, title, None, Gtk.DialogFlags.MODAL,
                            (_("Save"), Gtk.ResponseType.OK,
                             _("Cancel"), Gtk.ResponseType.CANCEL))

        self.set_transient_for(parent.get_toplevel())

        self.gen_store, self.action_stores = gen_store, action_stores
        self.treeview = Gtk.TreeView(self.gen_store)
        self.treeview.set_grid_lines(Gtk.TreeViewGridLines.BOTH)
        self.treeview.connect('button-press-event', self.on_button_press)

        '''
        # TODO: This does not work, find out why
        style_provider = Gtk.CssProvider()

        css = """
        GtkTreeView {
            even-row-color: #f0f0f0;            
        }
        """

        style "mystyle" {
            GtkTreeView::even_row_color = "xxxx"
            GtkTreeView::odd_row_color = "yyyy"
        }

        style_provider.load_from_data(css);

        Gtk.StyleContext.add_provider(style_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        '''

        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.on_toggled, self.M_COL_ENABLED)
        column = Gtk.TreeViewColumn(_("Enabled"), renderer, active = self.M_COL_ENABLED)
        self.treeview.append_column(column)

        renderer = MyCellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.M_COL_NAME)
        renderer.set_property('placeholder-text', '<name>')
        self.name_renderer = renderer
        column = Gtk.TreeViewColumn(_("Name"), renderer, text = self.M_COL_NAME)
        column.set_property('resizable', True)
        column.set_sort_column_id(self.M_COL_NAME)
        column.set_min_width(100)
        self.treeview.append_column(column)

        renderer = MyCellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.M_COL_PATTERN)
        renderer.set_property('placeholder-text', '<pattern>')
        column = Gtk.TreeViewColumn(_("Pattern"), renderer, text = self.M_COL_PATTERN)
        column.set_property('resizable', True)
        column.set_min_width(200)
        self.treeview.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn(_("Actions"), renderer)

        column.set_cell_data_func(renderer, self.do_summary)
        column.set_min_width(200)
        self.treeview.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.treeview)
        scrolled_window.set_min_content_height(200)

        self.vbox.pack_start(scrolled_window, False, False, 0)
        self.show_all()

    def is_gen_store_valid(self):
        for i, row in enumerate(self.gen_store):
            if not (row[self.M_COL_NAME] != "" and row[self.M_COL_PATTERN] != ""):
                md = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Error in row %s, fix it" % (i + 1))
                md.run()
                md.destroy()
                return False
        return True

    def get_gen_fields(self, pattern_row):
        return pattern_row[self.M_COL_KEY], pattern_row[self.M_COL_ENABLED], pattern_row[self.M_COL_NAME], pattern_row[self.M_COL_PATTERN]

    def get_action_fields(self, action_row):
        return action_row[self.AM_COL_KEY], action_row[self.AM_COL_COMMANDL], action_row[self.AM_COL_IN_TERMINAL], action_row[self.AM_COL_USE_SHELL]

    def do_summary(self, column, cell, gen_store, iter, user_data = None):

        key = gen_store[iter][self.M_COL_KEY]

        summary = ""
        sep = ""

        if self.action_stores.has_key(key):
            for action_row in self.action_stores[key]:
                summary = summary + sep + action_row[self.AM_COL_COMMANDL][0]
                sep = ', '

        else:
            summary = "<%s>" % _("Click to set actions")

        cell.set_property('text', summary)
        return

    def on_button_press(self, widget, event):

        if event.button != 1 and event.button != 3:
            return

        result = self.treeview.get_path_at_pos(int(event.x), int(event.y))
        inside = False
        path, col, x, y = None, None, None, None

        column_index = None
        if result != None:
            inside = True
            path, col, x, y = result
            self.treeview.get_selection().select_path(path)

            for i in range(0, self.treeview.get_n_columns()):
                if col == self.treeview.get_column(i):
                    column_index = i
                    break

        if inside and event.button == 1 and column_index == self.V_COL_ACTIONS:

            # popup with action list
            key = self.gen_store[path][self.M_COL_KEY]
            pattern = self.gen_store[path][self.M_COL_PATTERN]

            action_store = None
            if self.action_stores.has_key(key):
                action_store = self.action_stores[key]

            dialog = ActionDialog(self, key, pattern, action_store, "Commands for %s (%s)" % (key, pattern))

            while True:

                response = dialog.run()

                if response == Gtk.ResponseType.OK:
                    if dialog.is_store_valid():
                        self.action_stores[key] = dialog.action_store
                        break
                else:
                    break

            dialog.destroy()

        elif event.button == 3:

            # show new/delete menu
            menu = Gtk.Menu()

            if inside:
                item = Gtk.MenuItem.new_with_mnemonic(_('_Delete Pattern'))
                menu.append(item)
                item.connect('activate', self.delete_pattern, path)

            item = Gtk.MenuItem.new_with_mnemonic(_('_New Pattern'))
            menu.append(item)
            item.connect('activate', self.add_pattern)
            menu.show_all()
            menu.popup_at_pointer(event)


    def delete_pattern(self, widget, path):
        treeiter = self.gen_store.get_iter(path)
        self.gen_store.remove(treeiter)

    def add_pattern(self, widget):

        # find first available key
        keys = [int(row[self.M_COL_KEY]) for row in self.gen_store]

        expected = 1
        for key in sorted(keys):
            if key != expected:
                break
            expected = expected + 1

        iter = self.gen_store.append(("%s" % (expected), False, None, None))
        path = self.gen_store.get_path(iter)
        self.treeview.set_cursor(path, self.treeview.get_column(self.V_COL_NAME), True)

    # Debug
    def print_store(self, store):

        n = store.get_n_columns()

        for row in store:
            for i in range(0, n):
                print "%s" % row[i]

    def on_edited(self, widget, path, text, column):
        self.gen_store[path][column] = text

    def on_toggled(self, widget, path, column):
        self.gen_store[path][column] = not self.gen_store[path][column]

class ActionDialog(Gtk.Dialog):

    (M_COL_KEY, M_COL_COMMAND, M_COL_COMMANDL, M_COL_IN_TERMINAL, M_COL_USE_SHELL) = range(0, 5)
    (V_COL_COMMAND, V_COL_IN_TERMINAL, V_COL_USE_SHELL) = range(0, 3)

    def __init__(self, parent, key, pattern, action_store, title = 'TreeView'):

        Gtk.Dialog.__init__(self, title, parent, Gtk.DialogFlags.MODAL,
                            (_("Ok"), Gtk.ResponseType.OK,
                             _("Cancel"), Gtk.ResponseType.CANCEL))

        self.set_transient_for(parent)

        if action_store != None:
            self.action_store = self.copy_action_store(action_store)
        else:
            store_factory = StoreFactory()
            self.action_store = store_factory.create_action_store({})

        self.treeview = Gtk.TreeView(self.action_store)
        self.treeview.set_grid_lines(Gtk.TreeViewGridLines.BOTH)
        self.treeview.connect('button-press-event', self.on_button_press)

        renderer = MyCellRendererText()
        renderer.set_property("editable", True)
        renderer.set_property("placeholder-text", "<Command>")
        renderer.connect('edited', self.on_edited, self.M_COL_COMMAND)
        column = Gtk.TreeViewColumn(_("Command"), renderer, text = self.M_COL_COMMAND)
        column.set_property('resizable', True)
        column.set_sort_column_id(self.M_COL_COMMAND)
        column.set_min_width(200)
        self.treeview.append_column(column)

        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.on_toggled, self.M_COL_IN_TERMINAL)
        column = Gtk.TreeViewColumn(_("In Terminal"), renderer, active = self.M_COL_IN_TERMINAL)
        self.treeview.append_column(column)

        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.on_toggled, self.M_COL_USE_SHELL)
        column = Gtk.TreeViewColumn(_("Use Shell"), renderer, active = self.M_COL_USE_SHELL)
        self.treeview.append_column(column)

        upper_label = Gtk.Label('Actions for %s (%s)' % (pattern, key))

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.treeview)
        scrolled_window.set_min_content_height(200)

        self.vbox.pack_start(upper_label, False, False, 0)
        self.vbox.pack_start(scrolled_window, False, False, 0)

        self.show_all()

    # GObject objects are non-copyable blah blah blah
    def copy_action_store(self, action_store):

        ncols = action_store.get_n_columns()

        types = []

        for n in range(0, ncols):
            types.append(action_store.get_column_type(n))

        action_store_copy = Gtk.ListStore( *types )

        for row in action_store:
            action_store_copy.append(list(row))
        return action_store_copy

    def is_store_valid(self):
        for i, row in enumerate(self.action_store):
            if not (row[self.M_COL_COMMAND] != "" and len(row[self.M_COL_COMMANDL])):
                md = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Error in row %s, fix it" % (i + 1))
                md.run()
                md.destroy()
                return False
        return True

    def on_button_press(self, widget, event):

        if event.button != 3:
            return

        result = self.treeview.get_path_at_pos(int(event.x), int(event.y))
        inside = False
        path, col, x, y = None, None, None, None

        if result != None:
            inside = True
            path, col, x, y = result
            self.treeview.get_selection().select_path(path)

        menu = Gtk.Menu()

        if inside:
            item = Gtk.MenuItem.new_with_mnemonic(_('_Delete Command'))
            menu.append(item)
            item.connect('activate', self.delete_command, path)

        item = Gtk.MenuItem.new_with_mnemonic(_('_New Command'))
        menu.append(item)
        item.connect('activate', self.add_command)
        menu.show_all()
        menu.popup_at_pointer(event)

    def delete_command(self, widget, path):
        treeiter = self.action_store.get_iter(path)
        self.action_store.remove(treeiter)

    def add_command(self, widget):

        # find first available key
        keys = []
        for row in self.action_store:
            keys.append(int(row[self.M_COL_KEY]))

        expected = 1
        for key in sorted(keys):
            if key != expected:
                break
            expected = expected + 1

        iter = self.action_store.append( ( ("%s" % (expected)), "", [], False, False  ) )
        path = self.action_store.get_path(iter)
        self.treeview.set_cursor(path, self.treeview.get_column(self.V_COL_COMMAND), True)

    def on_edited(self, widget, path, text, column):
        self.action_store[path][column] = text
        if column == self.M_COL_COMMAND:
            self.action_store[path][self.M_COL_COMMANDL] = re.split(' +', text)

    def on_toggled(self, widget, path, column):
        self.action_store[path][column] = not self.action_store[path][column]

        if column == self.M_COL_IN_TERMINAL and self.action_store[path][column] == True:
            # if running in terminal, "use shell" makes no sense
            self.action_store[path][self.M_COL_USE_SHELL] = False
        else:
            if self.action_store[path][column] == True:
                # if "use shell" is true, cannot run in terminal
                self.action_store[path][self.M_COL_IN_TERMINAL] = False

class StoreFactory(Borg):

    def __init__(self):
        Borg.__init__(self, self.__class__.__name__)

    def create_gen_store(self, gen_config):

        gen_store = Gtk.ListStore(GObject.TYPE_STRING,      # key
                                  GObject.TYPE_BOOLEAN,     # enabled
                                  GObject.TYPE_STRING,      # name
                                  GObject.TYPE_STRING,      # pattern
                                  )

        for key in sorted(gen_config.keys()):
            a = gen_config[key]
            gen_store.append( (key, a['enabled'], a['name'], a['pattern']) )

        return gen_store


    def create_action_store(self, actions_config):

        action_store = Gtk.ListStore(GObject.TYPE_STRING,       # key
                                      GObject.TYPE_STRING,      # command
                                      GObject.TYPE_PYOBJECT,    # command as list
                                      GObject.TYPE_BOOLEAN,     # in terminal
                                      GObject.TYPE_BOOLEAN,     # use shell
                                      )

        for key in sorted(actions_config.keys()):
            a = actions_config[key]
            action_store.append( (key, ' '.join(a['command']), a['command'], a['in-terminal'], a['use-shell']) )

        return action_store

# Attempt at a sane CellRendererText. This saves changes
# even when the cell loses focus and editing is not finished,
# which is IMHO the expected behavior.
class MyCellRendererText(Gtk.CellRendererText):

    __gtype_name__ = "MyCellRendererText"

    def __init__(self):
        Gtk.CellRendererText.__init__(self)

    def do_start_editing(self, event, treeview, path, background_area, cell_area, flags):

        if not self.get_property('editable'):
            return

        self.canceled = False

        entry = Gtk.Entry()

        text = self.get_property('text')
        if text != None:
            entry.set_text(self.get_property('text'))

        entry.connect('key-press-event', self.on_key_press_event, path)

        entry.set_alignment(self.get_property('alignment'))
        entry.set_width_chars(5)
        entry.set_max_width_chars(self.get_property('width-chars'))

        entry.set_has_frame(False)
        entry.connect('focus-out-event', self.on_focus_out, path)

        entry.show()
        entry.grab_focus()

        return entry

    def on_key_press_event(self, widget, event, path):
        if event.keyval == Gdk.KEY_Escape:
            self.canceled = True
            self.emit("editing-canceled")

    def on_focus_out(self, entry, event, path):
        if self.canceled != True:
            self.emit('edited', path, entry.get_text())
