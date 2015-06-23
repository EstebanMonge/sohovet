# -*- encoding: utf-8 -*-
##############################################################################
#                                                                            #
#  OpenERP, Open Source Management Solution.                                 #
#                                                                            #
#  @author Juan Ignacio Alonso Barba <jialonso@grupovermon.com>              #
#                                                                            #
#  This program is free software: you can redistribute it and/or modify      #
#  it under the terms of the GNU Affero General Public License as            #
#  published by the Free Software Foundation, either version 3 of the        #
#  License, or (at your option) any later version.                           #
#                                                                            #
#  This program is distributed in the hope that it will be useful,           #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the              #
#  GNU Affero General Public License for more details.                       #
#                                                                            #
#  You should have received a copy of the GNU Affero General Public License  #
#  along with this program. If not, see <http://www.gnu.org/licenses/>.      #
#                                                                            #
##############################################################################

from openerp import fields, models, api, SUPERUSER_ID, _
from openerp.exceptions import ValidationError


class sohovet_product_brand_type(models.Model):
    _name = 'sohovet.product.brand.type'
    _description = 'Tipos de marcas de producto'

    name = fields.Char(string='Tipo', required='True')


class sohovet_product_brand(models.Model):
    _name = 'sohovet.product.brand'
    _description = 'Marca del producto'

    active = fields.Boolean(string='Activa', default=True)
    name = fields.Char(string='Nombre', required='True')
    type = fields.Many2one('sohovet.product.brand.type', 'Tipo')


class sohovet_product_group(models.Model):
    _name = 'sohovet.product.group'
    _description = 'Grupo del producto'

    # active = fields.Boolean(string='Activo', default=True)
    name = fields.Char(string='Nombre', required='True')
    description = fields.Char(string='Concepto')


########
## Product template
## - Añade marcas, ref. grupo
#######
class product_template(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('sohovet.product.brand', 'Marca')
    group_id = fields.Many2one('sohovet.product.group', 'Grupo')
    type = fields.Selection(default='product')

    default_code = fields.Char(readonly=True, copy=False)

    @api.model
    def create(self, vals):
        if not 'default_code' in vals:
            vals['default_code'] = self.env['ir.sequence'].next_by_code('product.template.sequence')
        res = super(product_template, self).create(vals)
        return res

class product_product(models.Model):
    _inherit = 'product.product'

    def name_get(self, cr, user, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        def _name_get(d):
            name = d.get('name','')
            code = context.get('display_default_code', True) and d.get('default_code',False) or False
            if code:
                name = '[%s] %s' % (code,name)
            return (d['id'], name)

        partner_id = context.get('partner_id', False)
        if partner_id:
            partner_ids = [partner_id, self.pool['res.partner'].browse(cr, user, partner_id, context=context).commercial_partner_id.id]
        else:
            partner_ids = []

        # all user don't have access to seller and partner
        # check access and use superuser
        self.check_access_rights(cr, user, "read")
        self.check_access_rule(cr, user, ids, "read", context=context)

        result = []
        for product in self.browse(cr, SUPERUSER_ID, ids, context=context):
            variant = ", ".join([v.name for v in product.attribute_value_ids])
            name = variant and "%s (%s)" % (product.name, variant) or product.name
            sellers = []
            if partner_ids:
                sellers = filter(lambda x: x.name.id in partner_ids, product.seller_ids)
            if sellers:
                for s in sellers:
                    seller_variant = variant and s.product_name and "%s (%s)" % (s.product_name, variant) or \
                                     s.product_name or False
                    mydict = {
                              'id': product.id,
                              'name': seller_variant or name,
                              'default_code': s.product_code or False,
                              }
                    result.append(_name_get(mydict))
            else:
                mydict = {
                          'id': product.id,
                          'name': name,
                          'default_code': False,
                          }
                result.append(_name_get(mydict))
        return result

class product_supplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    supplier_discount = fields.Integer('(%) Discount')

    @api.constrains('supplier_discount')
    def _check_discount(self):
        if self.supplier_discount and (self.supplier_discount < 0 or self.supplier_discount > 100):
            raise ValidationError(_('Discount should be a number between 0 and 100'))

    _sql_constraints = [
        ('product_code_uniq', 'unique(name, product_code)', _('Product code should be unique for each product of the'
                                                              'same provider'))
    ]
