# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2005 Async Open Source <http://www.async.com.br>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
##  Author(s): Evandro Vale Miquelito   <evandro@async.com.br>
##
"""
stoqlib/gui/lists.py:

    List management for common dialogs.
"""

import gettext

import gtk
from kiwi.ui.delegates import SlaveDelegate
from kiwi.utils import gsignal

from stoqlib.gui.dialogs import run_dialog, confirm_dialog
from stoqlib.gui.dialogs import BasicPluggableDialog, BasicDialog
from stoqlib.gui.editors import BaseEditor
from stoqlib.gui.search import BaseListSlave
from stoqlib.exceptions import SelectionError

_ = gettext.gettext

class AdditionListSlave(SlaveDelegate):
    """
    A slave that offers a simple list and its management. 
    """

    toplevel_name = gladefile = 'AdditionListSlave'
    widgets = ('add_button', 
               'delete_button', 
               'klist', 
               'list_vbox',
               'edit_button')
    gsignal('on-edit-item', object)
    gsignal('on-add-item', object)
    gsignal('before-delete-items', object)
    gsignal('after-delete-items')

    def __init__(self, conn, columns, editor_class=None, klist_objects=[]):
        """
        @param conn:          a connection
        @param editor_class:  the window that is going to be open when user 
          clicks on add_button or edit_button.
        @type: editor_class:  a L{stoqlib.gui.editors.BaseEditor} subclass
        @param columns:       columns definitions
        @type columns:        sequence of L{kiwi.ui.widgets.list.Columns}
        @param klist_objects: initial objects to insert into the list
        """
        if editor_class and not issubclass(editor_class, BaseEditor):
            raise TypeError("editor_class must be a BaseEditor subclass")
        
        SlaveDelegate.__init__(self, gladefile=self.gladefile, 
                               widgets=self.widgets)
        self.conn = conn
        self._editor_class = editor_class
        self._editor_kwargs = dict()
        self._columns = columns
        self.can_edit = True
        self._setup_klist(klist_objects)
        self._update_sensitivity()

    def _setup_klist(self, klist_objects):
        self.klist.set_columns(self._columns)
        self.klist.set_selection_mode(gtk.SELECTION_MULTIPLE)
        self.klist.add_list(klist_objects)

    def _update_sensitivity(self, *args):
        can_delete = can_edit = True
        objs = self.get_selection()
        if not objs:
            can_edit = can_delete = False
        elif len(objs) > 1:
            can_edit = False
            
        self.add_button.set_sensitive(True)
        self.edit_button.set_sensitive(can_edit)
        self.delete_button.set_sensitive(can_delete)

    def _run(self, model=None):
        edit_mode = model
        model = run_dialog(self._editor_class, None, conn=self.conn,
                           model=model, **self._editor_kwargs)
        if not model:
            return
        if edit_mode or model in self.klist:
            self.klist.update(model)
            self.emit('on-edit-item', model)
        else:
            self.klist.append(model)
            self.emit('on-add-item', model)

        # As we have a selection extended mode for kiwi list, we 
        # need to unselect everything before select the new instance.
        self.klist.unselect_all()
        self.klist.select(model)
        self._update_sensitivity()

    def _edit(self):
        if not self.can_edit:
            return
        objs = self.get_selection()
        qty = len(objs)
        if qty != 1:
            msg = ("Please select only one item before choosing Edit."
                   "\nThere are currently %d items selected")
            raise SelectionError(msg % qty)
        model = objs[0]
        self._run(model)

    def _clear(self):
        objs = self.get_selection()
        qty = len(objs)
        if qty < 1:
            raise SelectionError('There are no objects selected')

        if qty > 1:
            msg = _('Delete these %d items?' % qty)
        else:
            msg = _('Delete this item?')

        if not confirm_dialog(msg):
            return

        self.emit('before-delete-items', objs)
        if qty == len(self.klist):
            self.klist.clear()
        else:
            for obj in objs:
                self.klist.remove(obj)
        self.klist.unselect_all()
        self._update_sensitivity()
        self.emit('after-delete-items')

    #
    # Public API
    #

    def register_editor_kwargs(self, **kwargs):
        self._editor_kwargs = kwargs

    def get_selection(self):
        # XXX: add get_selected_rows and raise exceptions if not in the
        #      right mode
        if self.klist.get_selection_mode() == gtk.SELECTION_MULTIPLE:
            return self.klist.get_selected_rows()
        selection = self.klist.get_selected()
        if not selection:
            return []
        return [selection]

    def hide_add_button(self):
        self.add_button.hide()

    def hide_edit_button(self):
        self.can_edit = False
        self.edit_button.hide()

    def hide_del_button(self):
        self.del_button.hide()

    #
    # Signal handlers
    #

    def on_klist__double_click(self, *args):
        self._edit()

    def on_klist__selection_changed(self, *args):
        self._update_sensitivity()

    def on_add_button__clicked(self, *args):
        self._run()
    
    def on_edit_button__clicked(self, *args):
        self._edit()

    def on_delete_button__clicked(self, *args):
        self._clear()


class AdditionListDialog(BasicPluggableDialog):
    size = (500, 500)

    def __init__(self, conn, editor_class, columns, klist_objects, 
                 title=''):
        self.title = title
        BasicPluggableDialog.__init__(self)
        self.conn = conn
        self._initialize(editor_class, columns, klist_objects)

    def _initialize(self, editor_class, columns, klist_objects):
        self.addition_list = AdditionListSlave(self.conn, columns, 
                                               editor_class, klist_objects)
        self.addition_list.on_confirm = self.on_confirm
        self.addition_list.on_cancel = self.on_cancel
        self.addition_list.validate_confirm = self.validate_confirm
        BasicPluggableDialog._initialize(self, self.addition_list,
                                         size=self.size, title=self.title)

    def register_editor_kwargs(self, **kwargs):
        self.addition_list.register_editor_kwargs(**kwargs)

    def set_before_delete_items(self, callback):
        self.addition_list.connect('before-delete-items', callback)

    def set_on_add_item(self, callback):
        self.addition_list.connect('on-add-item', callback)

    def set_on_edit_item(self, callback):
        self.addition_list.connect('on-edit-item', callback)

    #
    # BasicPluggableDialog callbacks
    #

    def on_cancel(self):
        return

    def on_confirm(self):
        return self.addition_list.klist

    def validate_confirm(self):
        return True    


class SimpleListDialog(BasicDialog):
    size = (500, 400)

    def __init__(self, columns, objects, parent=None, hide_cancel_btn=True,
                 title='', selection_mode=gtk.SELECTION_MULTIPLE):
        BasicDialog.__init__(self)
        BasicDialog._initialize(self, size=self.size, title=title)

        if hide_cancel_btn:
            self.cancel_button.hide()

        self.setup_slave(columns, objects, parent, selection_mode)

    def setup_slave(self, columns, objects, parent, selection_mode):
        self.list_slave = BaseListSlave(parent, columns, objects)
        self.list_slave.klist.set_selection_mode(selection_mode)
        self.attach_slave('main', self.list_slave)

    def get_selection(self):
        mode = self.list_slave.klist.get_selection_mode() 
        if mode == gtk.SELECTION_MULTIPLE:
            return self.list_slave.klist.get_selected_rows()
        selection = self.list_slave.klist.get_selected()
        if not selection:
            return []
        return [selection]

    # BasicDialog 'confirm' method override
    def confirm(self):
        self.retval = self.get_selection()
        self.close()
