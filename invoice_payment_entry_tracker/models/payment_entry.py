from odoo import _, api, fields, models


class InvoicePaymentEntry(models.Model):
    _name = "invoice.payment.entry"
    _description = "Invoice Payment Entry"
    _order = "payment_date desc, id desc"

    name = fields.Char(required=True, copy=False, readonly=True, default=lambda self: _("New"))
    invoice_id = fields.Many2one("account.move", required=True, ondelete="cascade")
    payment_id = fields.Many2one("account.payment", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", related="invoice_id.partner_id", store=True)
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", required=True)
    payment_date = fields.Date(required=True)
    journal_id = fields.Many2one("account.journal", required=True)
    state = fields.Selection(related="payment_id.state", store=True)
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        required=True,
        domain="[('journal_id', '=', journal_id)]",
    )

    def action_open_payment(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "res_id": self.payment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("invoice.payment.entry") or _("New")
        return super().create(vals_list)
