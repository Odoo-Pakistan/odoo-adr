# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Agile Business Group sagl
#    (<http://www.agilebg.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from __future__ import division
from openerp.osv import fields, orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


class purchase_line_invoice(orm.TransientModel):

    _inherit = 'purchase.order.line_invoice'

    _columns = {
        'line_ids': fields.one2many('purchase.order.line_invoice.line',
                                    'wizard_id', 'Lines'),
    }

    def default_get(self, cr, uid, fields, context=None):
        po_line_obj = self.pool.get('purchase.order.line')
        lines = []
        for po_line in po_line_obj.browse(cr, uid,
                                          context.get('active_ids', []),
                                          context=context):
            lines.append({
                'po_line_id': po_line.id,
                'product_qty': po_line.product_qty - po_line.invoiced_qty,
                'invoiced_qty': po_line.product_qty - po_line.invoiced_qty,
                'price_unit': po_line.price_unit,
            })
        defaults = super(purchase_line_invoice, self).default_get(
            cr, uid, fields, context=context)
        defaults['line_ids'] = lines
        return defaults

    def makeInvoices(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        wizard = self.browse(cr, uid, ids[0], context=context)
        purchase_line_obj = self.pool.get('purchase.order.line')
        changed_lines = {}
        context['active_ids'] = []
        not_invoiced_ids = []
        invoiced_ids = []
        for line in wizard.line_ids:
            if line.invoiced_qty > line.product_qty:
                raise orm.except_orm(
                    _('Error'),
                    _("""Quantity to invoice is greater
                    than available quantity""")
                )
            context['active_ids'].append(line.po_line_id.id)
            changed_lines[
                line.po_line_id.id
            ] = line.invoiced_qty
            if line.po_line_id.fully_invoiced:
                invoiced_ids.append(line.po_line_id.id)
            else:
                not_invoiced_ids.append(line.po_line_id.id)
        if not_invoiced_ids:
            purchase_line_obj.write(cr, uid, not_invoiced_ids,
                                    {'invoiced': False})
        if invoiced_ids:
            purchase_line_obj.write(cr, uid, not_invoiced_ids,
                                    {'invoiced': True})
        ctx.update({'partial_quantity_lines': changed_lines})
        res = super(purchase_line_invoice, self).makeInvoices(
            cr, uid, ids, context=ctx)
        for po_line_id in changed_lines:
            po_line = purchase_line_obj.browse(cr, uid, po_line_id,
                                               context=context)
            if po_line.invoiced_qty != po_line.product_qty:
                po_line.write({'invoiced': False})
        return res


class purchase_line_invoice_line(orm.TransientModel):

    _name = 'purchase.order.line_invoice.line'

    _columns = {
        'po_line_id': fields.many2one(
            'purchase.order.line',
            'Purchase order line', readonly=True
        ),
        'product_qty': fields.float(
            'Quantity', digits_compute=dp.get_precision(
                'Product Unit of Measure'), readonly=True
        ),
        'price_unit': fields.related(
            'po_line_id', 'price_unit', type='float',
            string='Unit Price', readonly=True),
        'invoiced_qty': fields.float(
            'Quantity to invoice', digits_compute=dp.get_precision(
                'Product Unit of Measure')),
        'wizard_id': fields.many2one('purchase.order.line_invoice', 'Wizard'),
    }
