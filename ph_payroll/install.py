"""One-shot setup for ph_payroll.

Runs on ``bench install-app ph_payroll`` (after_install) and again on every
``bench migrate`` (after_migrate). Everything is idempotent: existing records
are left untouched, so your customisations survive updates.

Seeds:
- Employee custom fields (TIN, SSS No., PhilHealth No., Pag-IBIG MID, MWE flag)
- Statutory Salary Components (earnings, deductions, employer contributions)
- Salary Structures "PH Payroll - Monthly" and "PH Payroll - Semi-Monthly"
- PH Payroll Settings with the 2026 SSS / PhilHealth / Pag-IBIG / BIR tables
"""

import frappe

# ---------------------------------------------------------------------------
# Employee custom fields
# ---------------------------------------------------------------------------
EMPLOYEE_CUSTOM_FIELDS = [
    dict(
        fieldname="custom_tin",
        label="TIN",
        fieldtype="Data",
        insert_after="cell_number",
        description="BIR Tax Identification Number",
    ),
    dict(
        fieldname="custom_sss_number",
        label="SSS Number",
        fieldtype="Data",
        insert_after="custom_tin",
    ),
    dict(
        fieldname="custom_philhealth_number",
        label="PhilHealth Number",
        fieldtype="Data",
        insert_after="custom_sss_number",
    ),
    dict(
        fieldname="custom_hdmf_number",
        label="Pag-IBIG (HDMF) MID No.",
        fieldtype="Data",
        insert_after="custom_philhealth_number",
    ),
    dict(
        fieldname="custom_is_mwe",
        label="Minimum Wage Earner (MWE)",
        fieldtype="Check",
        insert_after="custom_hdmf_number",
        description=(
            "Exempt from income tax withholding (statutory minimum wage earner). "
            "Still pays SSS, PhilHealth and Pag-IBIG contributions."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Salary Components
# ---------------------------------------------------------------------------
BASIC = dict(
    salary_component="Basic Salary",
    salary_component_abbr="BASIC",
    type="Earning",
    amount_based_on_formula=1,
    formula="base",
    depends_on_payment_days=1,
    is_tax_applicable=1,
    remove_if_zero_valued=0,
    description=(
        "Basic pay. Set the Salary Structure Assignment base to the MONTHLY "
        "basic salary; the structure formula scales it per frequency "
        "(base for Monthly, base / 2 for semi-monthly)."
    ),
)

SALARY_COMPONENTS = [
    BASIC,
    dict(
        salary_component="Overtime Pay",
        salary_component_abbr="OT",
        type="Earning",
        is_tax_applicable=1,
        remove_if_zero_valued=1,
        description="Taxable overtime. Add per slip via Additional Salary or set an amount on the structure.",
    ),
    dict(
        salary_component="Allowance - Taxable",
        salary_component_abbr="TAXALLW",
        type="Earning",
        is_tax_applicable=1,
        remove_if_zero_valued=1,
        description="Taxable allowance.",
    ),
    dict(
        salary_component="Rice Subsidy",
        salary_component_abbr="RICESUB",
        type="Earning",
        is_tax_applicable=0,
        remove_if_zero_valued=1,
        description="De minimis rice subsidy (RR 29-2025): exempt from income tax within the monthly threshold.",
    ),
    dict(
        salary_component="13th Month Pay",
        salary_component_abbr="BONUS13",
        type="Earning",
        is_tax_applicable=0,
        remove_if_zero_valued=1,
        description=(
            "Exempt from income tax up to PHP 90,000 per calendar year (shared pool with other "
            "exempt benefits). Pay it in a December payroll run; any excess is taxable - adjust "
            "via an Additional Salary with a taxable component."
        ),
    ),
    dict(
        salary_component="SSS Employee Share",
        salary_component_abbr="SSS_EE",
        type="Deduction",
        remove_if_zero_valued=0,
        description="Computed by ph_payroll: 5% of MSC (PHP 5,000 - 35,000), split per cutoff.",
    ),
    dict(
        salary_component="PhilHealth Employee Share",
        salary_component_abbr="PH_EE",
        type="Deduction",
        remove_if_zero_valued=0,
        description="Computed by ph_payroll: 2.5% of premium base (PHP 10,000 - 100,000), split per cutoff.",
    ),
    dict(
        salary_component="Pag-IBIG Employee Share",
        salary_component_abbr="HDMF_EE",
        type="Deduction",
        remove_if_zero_valued=0,
        description=(
            "Computed by ph_payroll: 1% if monthly compensation <= PHP 1,500, "
            "else 2% capped at compensation PHP 10,000; split per cutoff."
        ),
    ),
    dict(
        salary_component="BIR Withholding Tax",
        salary_component_abbr="BIR_WTAX",
        type="Deduction",
        remove_if_zero_valued=0,
        description=(
            "Computed by ph_payroll: graduated withholding on annualized taxable pay "
            "(RA 12066 / CREATE MORE revised graduated rates, effective January 2026)."
        ),
    ),
    dict(
        salary_component="SSS Employer Share",
        salary_component_abbr="SSS_ER",
        type="Employer Contribution",
        remove_if_zero_valued=0,
        description="Computed by ph_payroll: 10% of MSC, split per cutoff.",
    ),
    dict(
        salary_component="SSS EC Contribution",
        salary_component_abbr="SSS_EC",
        type="Employer Contribution",
        remove_if_zero_valued=0,
        description="Computed by ph_payroll: PHP 30 if MSC >= 15,000, else PHP 10, split per cutoff.",
    ),
    dict(
        salary_component="PhilHealth Employer Share",
        salary_component_abbr="PH_ER",
        type="Employer Contribution",
        remove_if_zero_valued=0,
        description="Computed by ph_payroll: 2.5% of premium base, split per cutoff.",
    ),
    dict(
        salary_component="Pag-IBIG Employer Share",
        salary_component_abbr="HDMF_ER",
        type="Employer Contribution",
        remove_if_zero_valued=0,
        description="Computed by ph_payroll: 2% of compensation capped at PHP 10,000, split per cutoff.",
    ),
]

# ---------------------------------------------------------------------------
# Salary Structures
# ---------------------------------------------------------------------------
STRUCTURE_SPECS = [
    dict(name="PH Payroll - Monthly", payroll_frequency="Monthly", basic_formula="base"),
    dict(name="PH Payroll - Semi-Monthly", payroll_frequency="Bimonthly", basic_formula="base / 2"),
]

DEDUCTION_ROWS = [
    dict(salary_component="SSS Employee Share", abbr="SSS_EE"),
    dict(salary_component="PhilHealth Employee Share", abbr="PH_EE"),
    dict(salary_component="Pag-IBIG Employee Share", abbr="HDMF_EE"),
    dict(salary_component="BIR Withholding Tax", abbr="BIR_WTAX"),
]

EMPLOYER_ROWS = [
    dict(salary_component="SSS Employer Share", abbr="SSS_ER"),
    dict(salary_component="SSS EC Contribution", abbr="SSS_EC"),
    dict(salary_component="PhilHealth Employer Share", abbr="PH_ER"),
    dict(salary_component="Pag-IBIG Employer Share", abbr="HDMF_ER"),
]

# ---------------------------------------------------------------------------
# PH Payroll Settings defaults (2026)
# ---------------------------------------------------------------------------
SETTINGS_DEFAULTS = dict(
    rates_effective_from="2026-01-01",
    sss_ee_rate=5,
    sss_er_rate=10,
    sss_msc_min=5000,
    sss_msc_max=35000,
    sss_ec_small=10,
    sss_ec_big=30,
    sss_ec_msc_threshold=15000,
    philhealth_ee_rate=2.5,
    philhealth_floor=10000,
    philhealth_ceiling=100000,
    hdmf_ee_rate_low=1,
    hdmf_ee_rate_high=2,
    hdmf_low_comp_threshold=1500,
    hdmf_compensation_cap=10000,
    statutory_split_mode="Split per cutoff",
    mwe_tax_exempt=1,
)

BIR_BRACKETS_2026 = [
    dict(from_amount=0, to_amount=250000, percent_rate=0, base_tax=0),
    dict(from_amount=250000, to_amount=400000, percent_rate=15, base_tax=0),
    dict(from_amount=400000, to_amount=800000, percent_rate=20, base_tax=22500),
    dict(from_amount=800000, to_amount=2000000, percent_rate=25, base_tax=102500),
    dict(from_amount=2000000, to_amount=8000000, percent_rate=30, base_tax=402500),
    dict(from_amount=8000000, to_amount=0, percent_rate=35, base_tax=2202500),
]


def after_install():
    make_custom_fields()
    make_salary_components()
    make_salary_structures()
    make_settings()
    frappe.db.commit()


def after_migrate():
    # idempotent - keeps custom fields and records intact across updates
    make_custom_fields()
    make_salary_components()
    make_salary_structures()
    make_settings()


def make_custom_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

    create_custom_fields({"Employee": EMPLOYEE_CUSTOM_FIELDS}, ignore_validate=True, update=True)


def make_salary_components():
    for spec in SALARY_COMPONENTS:
        if frappe.db.exists("Salary Component", spec["salary_component"]):
            continue
        doc = frappe.get_doc({"doctype": "Salary Component", **spec})
        doc.flags.ignore_permissions = True
        doc.insert()


def make_salary_structures():
    companies = frappe.get_all("Company", pluck="name", limit=1)
    if not companies:
        frappe.msgprint(
            "ph_payroll: no Company exists yet, so the sample Salary Structures were not "
            "created. Create them manually or re-run bench migrate after adding a Company."
        )
        return

    company = companies[0]
    currency = frappe.get_cached_value("Company", company, "default_currency") or "PHP"

    for spec in STRUCTURE_SPECS:
        if frappe.db.exists("Salary Structure", spec["name"]):
            continue
        doc = frappe.get_doc(
            {
                "doctype": "Salary Structure",
                "name": spec["name"],
                "company": company,
                "is_active": "Yes",
                "payroll_frequency": spec["payroll_frequency"],
                "currency": currency,
                "earnings": [
                    {
                        "salary_component": "Basic Salary",
                        "abbr": "BASIC",
                        "is_tax_applicable": 1,
                        "amount_based_on_formula": 1,
                        "formula": spec["basic_formula"],
                        "depends_on_payment_days": 1,
                    },
                    {
                        "salary_component": "Overtime Pay",
                        "abbr": "OT",
                        "is_tax_applicable": 1,
                        "amount": 0,
                    },
                    {
                        "salary_component": "Allowance - Taxable",
                        "abbr": "TAXALLW",
                        "is_tax_applicable": 1,
                        "amount": 0,
                    },
                    {
                        "salary_component": "Rice Subsidy",
                        "abbr": "RICESUB",
                        "is_tax_applicable": 0,
                        "amount": 2500,
                        "depends_on_payment_days": 1,
                    },
                ],
                "deductions": DEDUCTION_ROWS,
                "employer_contributions": EMPLOYER_ROWS,
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()


def make_settings():
    if not frappe.db.exists("DocType", "PH Payroll Settings"):
        return

    settings = frappe.get_single("PH Payroll Settings")
    if settings.get("bir_brackets"):
        return  # already seeded - never overwrite user data

    settings.update(SETTINGS_DEFAULTS)
    for row in BIR_BRACKETS_2026:
        settings.append("bir_brackets", row)
    settings.flags.ignore_permissions = True
    settings.save()
