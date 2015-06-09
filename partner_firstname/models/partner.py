# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Copyright (C) 2014 Agile Business Group (<http://www.agilebg.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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
from openerp.osv import orm, fields
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class ResPartner(orm.Model):
    """Adds firstname and lastname, name become a stored function field"""

    _inherit = 'res.partner'

    def _set_default_value_on_column(self, cr, column_name, context=None):
        res = super(ResPartner, self)._set_default_value_on_column(
            cr, column_name, context=context)
        if column_name == 'firstname':
            cr.execute('UPDATE res_partner SET firstname = name WHERE name '
                       'IS NOT NULL AND firstname IS NULL')
            cr.execute('ALTER TABLE res_partner ALTER COLUMN firstname '
                       'SET NOT NULL')
            _logger.info("NOT NULL constraint for "
                         "res_partner.firstname correctly set")
        return res

    def _prepare_name_custom(self, cursor, uid, partner, context=None):
        """
        This function is designed to be inherited in a custom module
        """
        names = (partner.firstname, partner.lastname)
        fullname = " ".join([s for s in names if s])
        return fullname

    def _compute_name_custom(self, cursor, uid, ids, fname, arg, context=None):
        res = {}
        for partner in self.browse(cursor, uid, ids, context=context):
            res[partner.id] = self._prepare_name_custom(
                cursor, uid, partner, context=context)
        return res

    def _write_name(
        self, cursor, uid, partner_id, field_name, field_value, arg,
        context=None
    ):
        """
        Try to reverse the effect of _compute_name_custom:
        * if the partner is not a company and the lastname does not change in
          the new name then lastname remains untouched and firstname is updated
          accordingly
        * otherwise firstname=new name and lastname=False
        In addition an heuristic avoids to keep a lastname without a non-blank
        firstname
        """
        field_value = (
            field_value and not field_value.isspace() and field_value or False)
        vals = {'firstname': field_value, 'lastname': False}
        if field_value:
            flds = self.read(
                cursor, uid, [partner_id], ['lastname', 'is_company'],
                context=context)[0]
            if not flds['is_company']:
                to_check = ' %s' % flds['lastname']
                if field_value.endswith(to_check):
                    ln = field_value[:-len(to_check)].strip()
                    if ln:
                        vals['firstname'] = ln
                        del(vals['lastname'])
                    else:
                        # If the firstname is deleted from the new name
                        # then the lastname becomes the firstname
                        vals['firstname'] = flds['lastname']

        return self.write(cursor, uid, partner_id, vals, context=context)

    def copy_data(self, cr, uid, id, default=None, context=None):
        """
        Avoid to replicate the lastname into the name when duplicating a
        partner
        """
        default = default or {}
        if not default.get('firstname'):
            default = default.copy()
            default['firstname'] = (
                _('%s (copy)') % self.read(
                    cr, uid, [id], ['firstname'], context=context
                    )[0]['firstname']
            )
            if default.get('name'):
                del(default['name'])
        return super(ResPartner, self).copy_data(
            cr, uid, id, default, context=context)

    def create(self, cursor, uid, vals, context=None):
        """
        To support data backward compatibility we have to keep this overwrite
        even if we use fnct_inv: otherwise we can't create entry because
        firstname is mandatory and module will not install if there is demo data
        """
        corr_vals = vals.copy()
        if corr_vals.get('name'):
            corr_vals['firstname'] = corr_vals['name']
            del(corr_vals['name'])
        return super(ResPartner, self).create(
            cursor, uid, corr_vals, context=context)

    _columns = {'name': fields.function(_compute_name_custom, string="Name",
                                        type="char", store=True,
                                        select=True, readonly=True,
                                        fnct_inv=_write_name),

                'lastname': fields.char("Lastname"),
                'firstname': fields.char("Firstname", required=True)}
