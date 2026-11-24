"""Philippine statutory payroll computation for Frappe HR v16 salary slips.

Wired through ``override_doctype_class`` (see hooks.py). The override fills in:

+------------------------------+-----------------------------------+
| Deductions (employee share)  | Employer contributions            |
+==============================+===================================+
| SSS Employee Share           | SSS Employer Share                |
| PhilHealth Employee Share    | SSS EC Contribution               |
| Pag-IBIG Employee Share      | PhilHealth Employer Share         |
| BIR Withholding Tax          | Pag-IBIG Employer Share           |
+------------------------------+-----------------------------------+

The methods we override are hrms v16's official regional extension points
(``apply_regional_deductions`` / ``apply_regional_employer_contributions``);
they run at the right position inside ``calculate_net_pay()`` - after
structure deductions and loans, before totals - so the injected amounts flow
into total_deduction and net_pay for both saved slips and structure previews.

Monthly statutory amounts are derived from the slip's (prorated) Basic pay
and split across the pay periods per year (12 Monthly, 24 Bimonthly,
26 Fortnightly, 52 Weekly), so the same code handles Monthly and
semi-monthly payrolls. Rates come from the PH Payroll Settings single.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from hrms.payroll.doctype.salary_slip.salary_slip import (
    SalarySlip,
    get_salary_component_data,
)

try:
    from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
        PERIODS_PER_YEAR,
    )
except ImportError:  # older hrms: fall back to the same mapping
    PERIODS_PER_YEAR = {
        "Monthly": 12,
        "Fortnightly": 26,
        "Bimonthly": 24,
        "Weekly": 52,
        "Daily": 365,
    }

DEDUCTION_COMPONENTS = (
    "SSS Employee Share",
    "PhilHealth Employee Share",
    "Pag-IBIG Employee Share",
    "BIR Withholding Tax",
)

EMPLOYER_COMPONENTS = (
    "SSS Employer Share",
    "SSS EC Contribution",
    "PhilHealth Employer Share",
    "Pag-IBIG Employer Share",
)


def _is_philippine_company(company):
    return frappe.get_cached_value("Company", company, "country") == "Philippines"


class PHSalarySlip(SalarySlip):
    # ------------------------------------------------------------------
    # hrms v16 regional hook points
    # ------------------------------------------------------------------
    def apply_regional_deductions(self):
        if not _is_philippine_company(self.company):
            return
        amounts = self.get_ph_statutory_amounts()
        structure_components = self._get_structure_components("deductions")
        for component in DEDUCTION_COMPONENTS:
            if component not in structure_components:
                continue  # e.g. a 13th month structure must not carry SSS/tax
            amount = flt(amounts.get(_amount_key(component)), 2)
            self.update_component_row(
                get_salary_component_data(component), amount, "deductions"
            )

    def apply_regional_employer_contributions(self):
        if not _is_philippine_company(self.company):
            return
        amounts = self.get_ph_statutory_amounts()
        structure_components = self._get_structure_components("employer_contributions")
        for component in EMPLOYER_COMPONENTS:
            if component not in structure_components:
                continue
            amount = flt(amounts.get(_amount_key(component)), 2)
            self.update_component_row(
                get_salary_component_data(component), amount, "employer_contributions"
            )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _get_structure_components(self, parentfield):
        evaluated = getattr(self, "_evaluated_components", None)
        if not evaluated:
            self._set_evaluated_components()
            evaluated = self._evaluated_components
        return {row.salary_component for row in (evaluated.get(parentfield) or [])}

    def _get_ph_settings(self):
        if not frappe.db.exists("DocType", "PH Payroll Settings"):
            frappe.throw(
                _("PH Payroll Settings is missing. Run 'bench migrate' or reinstall ph_payroll.")
            )
        return frappe.get_cached_doc("PH Payroll Settings")

    def _get_ph_periods(self):
        frequency = self.payroll_frequency
        if not frequency and self.salary_structure:
            frequency = frappe.get_cached_value(
                "Salary Structure", self.salary_structure, "payroll_frequency"
            )
        periods = PERIODS_PER_YEAR.get(frequency or "")
        if not periods:
            frappe.throw(
                _(
                    "PH Payroll: payroll frequency '{0}' is not supported for statutory "
                    "computation. Use Monthly, Bimonthly (semi-monthly), Fortnightly or Weekly."
                ).format(frequency)
            )
        return periods

    def get_ph_statutory_amounts(self):
        """Return per-slip statutory amounts for this salary slip."""
        settings = self._get_ph_settings()
        periods = self._get_ph_periods()

        monthly = self._compute_monthly_statutory(settings)
        split_mode = (settings.statutory_split_mode or "Split per cutoff").strip()

        # Semi-monthly "second cutoff only": deduct the full monthly amount on
        # the 2nd cutoff (start day > 15), nothing on the 1st.
        if periods == 24 and split_mode == "Second cutoff only":
            if getdate(self.start_date).day <= 15:
                return frappe._dict({key: 0 for key in monthly})
            return frappe._dict({key: flt(value, 2) for key, value in monthly.items()})

        # Default: split the monthly amount evenly across the pay periods
        factor = 12.0 / periods
        return frappe._dict({key: flt(value * factor, 2) for key, value in monthly.items()})

    def _compute_monthly_statutory(self, settings):
        monthly_base = self._get_ph_monthly_compensation()

        msc = _clamp(monthly_base, flt(settings.sss_msc_min), flt(settings.sss_msc_max))

        sss_ee = msc * flt(settings.sss_ee_rate) / 100
        sss_er = msc * flt(settings.sss_er_rate) / 100
        sss_ec = (
            flt(settings.sss_ec_big)
            if msc >= flt(settings.sss_ec_msc_threshold)
            else flt(settings.sss_ec_small)
        )

        premium_base = _clamp(
            monthly_base, flt(settings.philhealth_floor), flt(settings.philhealth_ceiling)
        )
        philhealth_ee = premium_base * flt(settings.philhealth_ee_rate) / 100
        # Employer share mirrors the employee share (total premium split 50/50)
        philhealth_er = philhealth_ee

        if monthly_base <= flt(settings.hdmf_low_comp_threshold):
            pagibig_ee = monthly_base * flt(settings.hdmf_ee_rate_low) / 100
        else:
            pagibig_ee = (
                min(monthly_base, flt(settings.hdmf_compensation_cap))
                * flt(settings.hdmf_ee_rate_high)
                / 100
            )
        pagibig_er = (
            min(monthly_base, flt(settings.hdmf_compensation_cap))
            * flt(settings.hdmf_ee_rate_high)
            / 100
        )

        taxable_monthly = self._get_ph_taxable_monthly() - (
            sss_ee + philhealth_ee + pagibig_ee
        )
        bir_tax = self._get_ph_income_tax(settings, taxable_monthly)

        return frappe._dict(
            monthly_base=flt(monthly_base, 2),
            msc=flt(msc, 2),
            sss_ee=sss_ee,
            sss_er=sss_er,
            sss_ec=sss_ec,
            philhealth_ee=philhealth_ee,
            philhealth_er=philhealth_er,
            pagibig_ee=pagibig_ee,
            pagibig_er=pagibig_er,
            taxable_monthly=flt(taxable_monthly, 2),
            bir_tax=bir_tax,
        )

    def _get_ph_monthly_compensation(self):
        """Monthly compensation implied by this slip, based on prorated Basic pay.

        The Basic formula on each structure scales the (monthly) assignment base
        to the period (e.g. ``base / 2`` for Bimonthly), and hrms prorates it by
        payment days; multiplying back by periods/12 restores the monthly figure.
        """
        periods = self._get_ph_periods()
        basic = 0
        for row in self.get("earnings") or []:
            if row.abbr == "BASIC" or row.salary_component == "Basic Salary":
                basic = flt(row.amount)
                break

        if not basic:
            # Fallback: assignment base (monthly) scaled to the slip period the same
            # way the structure formula does (12/periods), then prorated by payment days
            try:
                if not hasattr(self, "_salary_structure_assignment"):
                    self.set_salary_structure_assignment()
                ratio = (
                    flt(self.payment_days) / cint(self.total_working_days)
                    if cint(self.total_working_days)
                    else 1
                )
                basic = flt(self._salary_structure_assignment.base) * ratio * (12.0 / periods)
            except Exception:
                basic = 0

        # period amount -> monthly compensation (e.g. Bimonthly basic x 24/12)
        return basic * periods / 12.0

    def _get_ph_taxable_monthly(self):
        """Monthly taxable gross: earnings flagged is_tax_applicable on the slip.

        Non-taxable earnings (13th month, de minimis such as Rice Subsidy) are
        left out because their Salary Detail rows carry is_tax_applicable = 0.
        """
        periods = self._get_ph_periods()
        taxable = 0
        for row in self.get("earnings") or []:
            if row.do_not_include_in_total:
                continue
            if row.is_tax_applicable:
                taxable += flt(row.amount)
        # period amounts -> monthly (e.g. Bimonthly x 24/12)
        return taxable * periods / 12.0

    def _get_ph_income_tax(self, settings, taxable_monthly):
        if taxable_monthly <= 0:
            return 0

        employee = frappe.get_cached_doc("Employee", self.employee)
        if settings.mwe_tax_exempt and _is_mwe(employee):
            return 0

        annual_taxable = taxable_monthly * 12
        annual_tax = 0
        for bracket in sorted(settings.bir_brackets or [], key=lambda d: flt(d.from_amount)):
            lower = flt(bracket.from_amount)
            upper = flt(bracket.to_amount) or float("inf")  # 0 = no upper limit
            rate = flt(bracket.percent_rate)
            if annual_taxable > lower:
                annual_tax += (min(annual_taxable, upper) - lower) * rate / 100

        return annual_tax / 12


def _amount_key(component):
    return {
        "SSS Employee Share": "sss_ee",
        "PhilHealth Employee Share": "philhealth_ee",
        "Pag-IBIG Employee Share": "pagibig_ee",
        "BIR Withholding Tax": "bir_tax",
        "SSS Employer Share": "sss_er",
        "SSS EC Contribution": "sss_ec",
        "PhilHealth Employer Share": "philhealth_er",
        "Pag-IBIG Employer Share": "pagibig_er",
    }[component]


def _clamp(value, lower, upper):
    return max(lower, min(value, upper))


def _is_mwe(employee):
    # custom field created by ph_payroll.install (v15+ prefixes custom_)
    return bool(employee.get("custom_is_mwe") or employee.get("is_mwe"))
