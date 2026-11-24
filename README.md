# ph_payroll

Philippine payroll localization for Frappe HR (hrms) v16.

- SSS, PhilHealth and Pag-IBIG (HDMF) employee shares and employer contributions
- BIR graduated withholding tax on annualized taxable pay
- Works with Monthly and semi-monthly (Bimonthly) payrolls out of the box
- All rates are editable in **PH Payroll Settings** (2026 tables pre-loaded)

Install (bench / local):

```sh
bench get-app /path/to/ph_payroll     # or a git URL
bench install-app ph_payroll
bench migrate && bench restart
```

After install the app creates: statutory Salary Components, the salary
structures *PH Payroll - Monthly* and *PH Payroll - Semi-Monthly*, the
**PH Payroll Settings** single (with 2026 SSS/PhilHealth/Pag-IBIG/BIR values)
and TIN / SSS / PhilHealth / Pag-IBIG / MWE fields on Employee.

See the package README (one level up) for the full guide, including the
frappe_docker `apps.json` build path.
# test_hr_repo
# test_hr_repo
# test_hr_repo
