import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PHPayrollSettings(Document):
    def validate(self):
        self.validate_bir_brackets()

    def validate_bir_brackets(self):
        if not self.bir_brackets:
            frappe.throw(_("Please add at least one BIR withholding tax bracket."))

        prev_to = 0
        for row in sorted(self.bir_brackets, key=lambda d: flt(d.from_amount)):
            if flt(row.from_amount) < prev_to and flt(row.to_amount):
                frappe.throw(
                    _("Row {0}: brackets overlap with the previous row.").format(row.idx)
                )
            if flt(row.to_amount) and flt(row.to_amount) <= flt(row.from_amount):
                frappe.throw(
                    _("Row {0}: 'To' must be greater than 'From' (or 0 for the top bracket).").format(
                        row.idx
                    )
                )
            prev_to = flt(row.to_amount)
