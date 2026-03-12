{
    "name": "Invoice Payment Entry Tracker",
    "version": "18.0.1.0.0",
    "summary": "Track payments created from customer invoices",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/payment_entry_views.xml",
        "views/account_move_views.xml",
        "wizard/invoice_payment_wizard_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
