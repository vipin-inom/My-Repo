from odoo import fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_entry_count = fields.Integer(compute="_compute_payment_entry_count")

    def _compute_payment_entry_count(self):
        grouped = self.env["invoice.payment.entry"].read_group(
            [("invoice_id", "in", self.ids)],
            ["invoice_id"],
            ["invoice_id"],
        )
        count_map = {row["invoice_id"][0]: row["invoice_id_count"] for row in grouped}
        for move in self:
            move.payment_entry_count = count_map.get(move.id, 0)

    def action_open_invoice_payment_wizard(self):
        self.ensure_one()
        self._check_payment_allowed()
        return {
            "name": "Payment",
            "type": "ir.actions.act_window",
            "res_model": "invoice.payment.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invoice_id": self.id,
            },
        }

    def action_view_payment_entries(self):
        self.ensure_one()
        action = self.env.ref("invoice_payment_entry_tracker.action_invoice_payment_entry").read()[0]
        action["domain"] = [("invoice_id", "=", self.id)]
        action["context"] = {"default_invoice_id": self.id}
        return action

    def action_reconcile_payment_entries(self):
        self.ensure_one()
        self._check_payment_allowed()

        payment_entries = self.env["invoice.payment.entry"].search(
            [("invoice_id", "=", self.id)]
        )
        if not payment_entries:
            raise ValidationError("No payment entries were found for this invoice.")

        payments = payment_entries.mapped("payment_id").filtered(
            lambda payment: payment.state != "cancel"
        )
        if not payments:
            raise ValidationError("No valid payments were found to reconcile.")

        draft_payments = payments.filtered(lambda payment: payment.state == "draft")
        if draft_payments:
            draft_payments.action_post()

        receivable_lines = self.line_ids.filtered(
            lambda line: line.account_type == "asset_receivable" and not line.reconciled
        )
        payment_lines = payments.mapped("move_id.line_ids").filtered(
            lambda line: line.account_type == "asset_receivable" and not line.reconciled
        )

        lines_to_reconcile = receivable_lines + payment_lines
        if not lines_to_reconcile:
            raise ValidationError("There are no outstanding receivable lines to reconcile.")

        lines_to_reconcile.reconcile()

    def _check_payment_allowed(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            raise ValidationError("Payments can only be registered from customer invoices.")
        if self.state != "posted":
            raise ValidationError("Only posted invoices can be paid.")
        if self.payment_state == "paid":
            raise ValidationError("This invoice is already fully paid.")
