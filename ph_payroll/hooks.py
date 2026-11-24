app_name = "ph_payroll"
app_title = "PH Payroll"
app_publisher = "PH Payroll Contributors"
app_description = (
    "Philippine payroll localization (SSS, PhilHealth, Pag-IBIG and BIR "
    "graduated withholding) for Frappe HR (hrms) v16"
)
app_email = "admin@example.com"
app_license = "mit"

# ---------------------------------------------------------------------------
# Salary Slip override - Philippines statutory payroll
# ---------------------------------------------------------------------------
# hrms v16 exposes two official regional extension points on the Salary Slip:
#
#   - SalarySlip.apply_regional_deductions()
#     runs AFTER structure deductions (incl. Additional Salary and loan
#     repayments) and BEFORE totals are set;
#   - SalarySlip.apply_regional_employer_contributions()
#     runs AFTER structure employer contributions and BEFORE totals.
#
# Both are invoked from SalarySlip.calculate_net_pay() for every slip
# (including Salary Structure previews), so amounts injected there flow into
# total_deduction / net_pay correctly.
#
# We wire them through override_doctype_class (always triggers, regardless of
# the System Settings "country"); the override itself checks
# Company.country == "Philippines" so it stays inert for other countries.
override_doctype_class = {
    "Salary Slip": ["ph_payroll.ph_payroll.overrides.salary_slip.PHSalarySlip"]
}

after_install = "ph_payroll.install.after_install"
after_migrate = "ph_payroll.install.after_migrate"
