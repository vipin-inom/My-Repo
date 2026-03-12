from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class InvoicePaymentWizard(models.TransientModel):
    _name = "invoice.payment.wizard"
    _description = "Invoice Payment Wizard"

    invoice_id = fields.Many2one("account.move", required=True, readonly=True)
    partner_id = fields.Many2one(related="invoice_id.partner_id", readonly=True)
    currency_id = fields.Many2one(related="invoice_id.currency_id", readonly=True)
    company_id = fields.Many2one(related="invoice_id.company_id", readonly=True)
    amount = fields.Monetary(required=True)
    payment_date = fields.Date(required=True, default=fields.Date.context_today)
    journal_id = fields.Many2one(
        "account.journal",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        required=True,
        domain="[('journal_id', '=', journal_id)]",
    )
    communication = fields.Char(string="Memo")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        invoice = self.env["account.move"].browse(values.get("invoice_id"))
        if invoice:
            values.setdefault("amount", invoice.amount_residual)
            values.setdefault("communication", invoice.name)
        return values

    def action_create_payment(self):
        self.ensure_one()
        invoice = self.invoice_id
        invoice._check_payment_allowed()

        if self.amount <= 0:
            raise ValidationError(_("Payment amount must be greater than zero."))

        payment_vals = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": invoice.partner_id.id,
            "amount": self.amount,
            "currency_id": invoice.currency_id.id,
            "date": self.payment_date,
            "journal_id": self.journal_id.id,
            "payment_method_line_id": self.payment_method_line_id.id,
            "payment_reference": self.communication or invoice.name,
            "company_id": invoice.company_id.id,
        }
        # payment = self.env["account.payment"].create(payment_vals)
        # payment.action_post()

        invoice_payment=self.env["invoice.payment.entry"].create(
            {
                "invoice_id": invoice.id,
                # "payment_id": payment.id,
                "amount": self.amount,
                "currency_id": invoice.currency_id.id,
                "payment_date": self.payment_date,
                "journal_id": self.journal_id.id,
                "payment_method_line_id":self.payment_method_line_id.id,
            }
        )

        receivable_lines = invoice.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable" and not line.reconciled
        )
        payment_lines = invoice_payment.invoice_id.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable" and not line.reconciled
        )
        (receivable_lines + payment_lines).reconcile()

        return {"type": "ir.actions.act_window_close"}
