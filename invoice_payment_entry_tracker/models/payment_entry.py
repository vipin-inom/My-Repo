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
    due_amount = fields.Monetary(
        string="Due Amount",
        compute="_compute_due_amount",
        currency_field="currency_id",
    )
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

    @api.depends("invoice_id", "invoice_id.amount_total", "amount", "payment_date")
    def _compute_due_amount(self):
        entries_by_invoice = {}
        for entry in self.filtered("invoice_id"):
            entries_by_invoice.setdefault(entry.invoice_id, self.env["invoice.payment.entry"])
            entries_by_invoice[entry.invoice_id] |= entry

        for invoice, current_entries in entries_by_invoice.items():
            all_entries = self.search(
                [("invoice_id", "=", invoice.id)],
                order="payment_date asc, id asc",
            )
            running_paid = 0.0
            due_map = {}
            for payment_entry in all_entries:
                running_paid += payment_entry.amount
                due_map[payment_entry.id] = max(invoice.amount_total - running_paid, 0.0)

            for current_entry in current_entries:
                current_entry.due_amount = due_map.get(current_entry.id, invoice.amount_total)

        for entry in self.filtered(lambda rec: not rec.invoice_id):
            entry.due_amount = 0.0
