
import math

import frappe
from frappe.utils import add_days, add_years, flt, getdate


MRA_MONTHLY_PAYE_PERIODS = 13


def apply_regional_deductions(salary_slip):
    """
    Apply Mauritius-specific PAYE calculation.

    Version 0.7:
    - Monthly payroll only
    - July through December, with December salary + EOY bonus as PAYE period 7
    - Cumulative taxable emoluments
    - Previous PAYE deducted
    - No EDF yet
    - No prescribed EOY bonus yet
    """

    # Version 0.2 supports monthly payroll only.
    if salary_slip.payroll_frequency != "Monthly":
        return

    start_date = getdate(salary_slip.start_date)

    period_number = get_mauritius_period_number(start_date)

    # December regular salary is PAYE period 6.
    # It becomes period 7 only when the prescribed EOY bonus
    # is actually present on the Salary Slip.
    if (
        start_date.month == 12
        and get_mauritius_csg_base(
            salary_slip,
            "Prescribed EOY Bonus",
        ) > 0
    ):
        period_number = 7

    if not period_number:
        return

    # Mauritius employee CSG is independent of PAYE.
    apply_mauritius_csg_employee(salary_slip)
    apply_mauritius_csg_employer(salary_slip)
    apply_mauritius_csg_eoy_bonus(salary_slip)
    apply_mauritius_nsf(salary_slip)
    apply_mauritius_hrdc_levy(salary_slip)
    apply_mauritius_prgf(salary_slip)


    # Prepare tax slab for FSC.
    if not getattr(salary_slip, "_salary_structure_assignment", None):
        salary_slip.set_salary_structure_assignment()

    if not getattr(salary_slip, "tax_slab", None):
        salary_slip.tax_slab = salary_slip.get_income_tax_slabs()

    # Apply Mauritius FSC independently of PAYE.
    apply_mauritius_fsc(salary_slip)


    # Find the deduction component configured as Income Tax.
    tax_row = get_income_tax_row(salary_slip)

    if not tax_row:
        return

    # Use the Income Tax Slab selected on the
    # Salary Structure Assignment.
    tax_slab = getattr(salary_slip, "tax_slab", None)

    if not tax_slab:
        tax_slab = salary_slip.get_income_tax_slabs()

    # Current Salary Slip taxable emoluments.
    current_taxable_emoluments = get_current_taxable_emoluments(
        salary_slip
    )

    # Taxable emoluments from previous submitted Salary Slips.
    previous_taxable_emoluments = get_previous_taxable_emoluments(
        salary_slip
    )

    cumulative_taxable_emoluments = (
        previous_taxable_emoluments
        + current_taxable_emoluments
    )

    # Current annual EDF relief for reference/display.
    annual_edf_relief = get_annual_edf_relief(
        salary_slip
    )

    # Cumulative Mauritius EDF relief, including any
    # mid-year EDF revisions and their applicable variance.
    cumulative_edf_relief = get_cumulative_edf_relief(
        salary_slip,
        period_number,
    )

    cumulative_chargeable_income = max(
        0,
        cumulative_taxable_emoluments - cumulative_edf_relief,
    )



    # Calculate cumulative Mauritius tax using the relevant
    # fraction of the annual bands.
    cumulative_tax = calculate_mauritius_cumulative_tax(
        taxable_emoluments=cumulative_chargeable_income,
        tax_slab=tax_slab,
        period_number=period_number,
    )

    # Mauritius PAYE is rounded DOWN to the nearest rupee.
    cumulative_tax = math.floor(max(0, cumulative_tax))

    # PAYE already deducted on previous submitted Salary Slips.
    previous_paye = get_previous_paye(
        salary_slip,
        tax_row.salary_component,
    )

    # Current PAYE is cumulative liability less PAYE
    # already deducted.
    current_paye = max(
        0,
        cumulative_tax - math.floor(previous_paye),
    )

    # Replace ERPNext's standard tax amount.
    tax_row.amount = current_paye

    # Keep base amount consistent with Salary Slip currency conversion.
    tax_row.base_amount = (
        current_paye * flt(salary_slip.exchange_rate or 1)
    )



def get_mauritius_csg_base(salary_slip, treatment):
    total = 0
    for row in salary_slip.get("earnings", []):
        component_treatment = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            "custom_mauritius_csg_treatment",
        )
        if component_treatment == treatment:
            total += flt(row.amount)
    return total


def apply_mauritius_csg_employee(salary_slip):
    regular_base = get_mauritius_csg_base(
        salary_slip,
        "Regular Remuneration",
    )

    if regular_base <= 0:
        add_mauritius_csg_component(
            salary_slip, "CSG Employee", 0, "deductions"
        )
        return

    if not frappe.db.exists("Salary Component", "CSG Employee"):
        return

    employee_rate = 0.015 if regular_base <= 50000 else 0.03
    precision = frappe.get_precision("Salary Detail", "amount") or 2
    csg_amount = flt(regular_base * employee_rate, precision)

    component = frappe.get_cached_doc("Salary Component", "CSG Employee")
    component_data = frappe._dict({
        "salary_component": component.name,
        "abbr": component.salary_component_abbr,
        "depends_on_payment_days": component.get("depends_on_payment_days"),
        "do_not_include_in_total": component.get("do_not_include_in_total"),
        "do_not_include_in_accounts": component.get("do_not_include_in_accounts"),
        "accrual_component": component.get("accrual_component"),
        "is_tax_applicable": component.get("is_tax_applicable"),
        "is_flexible_benefit": component.get("is_flexible_benefit"),
        "variable_based_on_taxable_salary": component.get("variable_based_on_taxable_salary"),
        "exempted_from_income_tax": component.get("exempted_from_income_tax"),
        "deduct_full_tax_on_selected_payroll_date": component.get("deduct_full_tax_on_selected_payroll_date"),
    })

    salary_slip.update_component_row(
        component_data,
        csg_amount,
        "deductions",
        default_amount=csg_amount,
        remove_if_zero_valued=1,
    )


def apply_mauritius_csg_employer(salary_slip):
    regular_base = get_mauritius_csg_base(
        salary_slip,
        "Regular Remuneration",
    )

    if regular_base <= 0:
        add_mauritius_csg_component(
            salary_slip, "CSG Employer", 0, "employer_contributions"
        )
        return

    if not frappe.db.exists("Salary Component", "CSG Employer"):
        return

    employer_rate = 0.03 if regular_base <= 50000 else 0.06
    precision = frappe.get_precision("Salary Detail", "amount") or 2
    csg_amount = flt(regular_base * employer_rate, precision)

    component = frappe.get_cached_doc("Salary Component", "CSG Employer")
    component_data = frappe._dict({
        "salary_component": component.name,
        "abbr": component.salary_component_abbr,
        "depends_on_payment_days": component.get("depends_on_payment_days"),
        "do_not_include_in_total": component.get("do_not_include_in_total"),
        "do_not_include_in_accounts": component.get("do_not_include_in_accounts"),
        "accrual_component": component.get("accrual_component"),
        "is_tax_applicable": component.get("is_tax_applicable"),
        "is_flexible_benefit": component.get("is_flexible_benefit"),
        "variable_based_on_taxable_salary": component.get("variable_based_on_taxable_salary"),
        "exempted_from_income_tax": component.get("exempted_from_income_tax"),
        "deduct_full_tax_on_selected_payroll_date": component.get("deduct_full_tax_on_selected_payroll_date"),
    })

    salary_slip.update_component_row(
        component_data,
        csg_amount,
        "employer_contributions",
        default_amount=csg_amount,
        remove_if_zero_valued=1,
    )


def get_previous_prescribed_eoy_bonus(salary_slip):
    start_date = getdate(salary_slip.start_date)
    year_start = getdate(f"{start_date.year}-01-01")

    previous_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "employee": salary_slip.employee,
            "company": salary_slip.company,
            "docstatus": 1,
            "start_date": ["between", [year_start, add_days(start_date, -1)]],
        },
        pluck="name",
    )

    if not previous_slips:
        return 0

    rows = frappe.get_all(
        "Salary Detail",
        filters={
            "parent": ["in", previous_slips],
            "parenttype": "Salary Slip",
            "parentfield": "earnings",
        },
        fields=["salary_component", "amount"],
    )

    total = 0
    for row in rows:
        treatment = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            "custom_mauritius_csg_treatment",
        )
        if treatment == "Prescribed EOY Bonus":
            total += flt(row.amount)

    return total


def add_mauritius_csg_component(salary_slip, component_name, amount, component_type):
    if not frappe.db.exists("Salary Component", component_name):
        return

    component = frappe.get_cached_doc("Salary Component", component_name)
    component_data = frappe._dict({
        "salary_component": component.name,
        "abbr": component.salary_component_abbr,
        "depends_on_payment_days": component.get("depends_on_payment_days"),
        "do_not_include_in_total": component.get("do_not_include_in_total"),
        "do_not_include_in_accounts": component.get("do_not_include_in_accounts"),
        "accrual_component": component.get("accrual_component"),
        "is_tax_applicable": component.get("is_tax_applicable"),
        "is_flexible_benefit": component.get("is_flexible_benefit"),
        "variable_based_on_taxable_salary": component.get("variable_based_on_taxable_salary"),
        "exempted_from_income_tax": component.get("exempted_from_income_tax"),
        "deduct_full_tax_on_selected_payroll_date": component.get("deduct_full_tax_on_selected_payroll_date"),
    })

    salary_slip.update_component_row(
        component_data,
        amount,
        component_type,
        default_amount=amount,
        remove_if_zero_valued=1,
    )


def apply_mauritius_csg_eoy_bonus(salary_slip):
    current_bonus = get_mauritius_csg_base(
        salary_slip,
        "Prescribed EOY Bonus",
    )

    if current_bonus <= 0:
        add_mauritius_csg_component(
            salary_slip, "CSG Employee - EOY Bonus", 0, "deductions"
        )
        add_mauritius_csg_component(
            salary_slip, "CSG Employer - EOY Bonus", 0, "employer_contributions"
        )
        return

    previous_bonus = get_previous_prescribed_eoy_bonus(salary_slip)
    cumulative_bonus = previous_bonus + current_bonus

    employee_rate = 0.015 if cumulative_bonus <= 50000 else 0.03
    employer_rate = 0.03 if cumulative_bonus <= 50000 else 0.06
    precision = frappe.get_precision("Salary Detail", "amount") or 2

    employee_csg = flt(current_bonus * employee_rate, precision)
    employer_csg = flt(current_bonus * employer_rate, precision)

    add_mauritius_csg_component(
        salary_slip,
        "CSG Employee - EOY Bonus",
        employee_csg,
        "deductions",
    )
    add_mauritius_csg_component(
        salary_slip,
        "CSG Employer - EOY Bonus",
        employer_csg,
        "employer_contributions",
    )


def is_mauritius_nsf_age_eligible(salary_slip):
    date_of_birth = frappe.db.get_value(
        "Employee",
        salary_slip.employee,
        "date_of_birth",
    )

    if not date_of_birth:
        frappe.throw("Date of Birth is required to determine Mauritius NSF eligibility.")

    date_of_birth = getdate(date_of_birth)
    start_date = getdate(salary_slip.start_date)
    end_date = getdate(salary_slip.end_date)

    eighteenth_birthday = add_years(date_of_birth, 18)
    retirement_birthday = add_years(date_of_birth, 65)

    if end_date < eighteenth_birthday:
        return False

    if start_date >= retirement_birthday:
        return False

    if start_date < eighteenth_birthday <= end_date:
        frappe.throw(
            "Employee attains age 18 during this payroll period. Review NSF treatment for the transition month before processing payroll."
        )

    if start_date < retirement_birthday <= end_date:
        frappe.throw(
            "Employee attains retirement age 65 during this payroll period. Review NSF treatment for the transition month before processing payroll."
        )

    return True


def get_mauritius_nsf_base(salary_slip):
    total = 0
    for row in salary_slip.get("earnings", []):
        is_nsf_base = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            "custom_mauritius_nsf_base",
        )
        if is_nsf_base:
            total += flt(row.amount)
    return total


def apply_mauritius_nsf(salary_slip):
    raw_base = get_mauritius_nsf_base(salary_slip)

    if raw_base <= 0 or not is_mauritius_nsf_age_eligible(salary_slip):
        add_mauritius_csg_component(
            salary_slip, "NSF Employee", 0, "deductions"
        )
        add_mauritius_csg_component(
            salary_slip, "NSF Employer", 0, "employer_contributions"
        )
        return

    # Monthly NSF insurable salary for employees outside private households,
    # effective 01 July 2026.
    insured_base = min(max(raw_base, 4580), 29710)

    # NSF is rounded to the nearest whole rupee (0.50 rounds upward).
    employee_nsf = math.floor((insured_base * 0.01) + 0.5)
    employer_nsf = math.floor((insured_base * 0.025) + 0.5)

    add_mauritius_csg_component(
        salary_slip,
        "NSF Employee",
        employee_nsf,
        "deductions",
    )
    add_mauritius_csg_component(
        salary_slip,
        "NSF Employer",
        employer_nsf,
        "employer_contributions",
    )


def get_mauritius_prgf_monthly_basic_salary(salary_slip):
    assignments = frappe.get_all(
        "Salary Structure Assignment",
        filters={
            "employee": salary_slip.employee,
            "docstatus": 1,
            "from_date": ["<=", salary_slip.end_date],
        },
        fields=["base"],
        order_by="from_date desc",
        limit=1,
    )

    if not assignments:
        frappe.throw(
            "A submitted Salary Structure Assignment is required to determine Mauritius PRGF eligibility."
        )

    return flt(assignments[0].base)


def is_mauritius_prgf_eligible(salary_slip):
    employee = frappe.db.get_value(
        "Employee",
        salary_slip.employee,
        ["date_of_birth", "custom_mauritius_prgf_exemption"],
        as_dict=True,
    )

    if not employee or not employee.date_of_birth:
        frappe.throw("Date of Birth is required to determine Mauritius PRGF eligibility.")

    date_of_birth = getdate(employee.date_of_birth)
    start_date = getdate(salary_slip.start_date)
    end_date = getdate(salary_slip.end_date)
    sixteenth_birthday = add_years(date_of_birth, 16)

    if end_date < sixteenth_birthday:
        return False

    if start_date < sixteenth_birthday <= end_date:
        frappe.throw(
            "Employee attains age 16 during this payroll period. Review PRGF treatment for the transition month before processing payroll."
        )

    if (employee.custom_mauritius_prgf_exemption or "").strip():
        return False

    monthly_basic_salary = get_mauritius_prgf_monthly_basic_salary(salary_slip)
    if monthly_basic_salary > 200000:
        return False

    return True


def get_mauritius_prgf_base(salary_slip):
    total = 0
    for row in salary_slip.get("earnings", []):
        is_prgf_base = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            "custom_mauritius_prgf_base",
        )
        if is_prgf_base:
            total += flt(row.amount)
    return total


def apply_mauritius_prgf(salary_slip):
    prgf_base = get_mauritius_prgf_base(salary_slip)

    if prgf_base <= 0:
        contribution = 0
    elif not is_mauritius_prgf_eligible(salary_slip):
        contribution = 0
    else:
        precision = frappe.get_precision("Salary Detail", "amount") or 2
        contribution = flt(prgf_base * 0.045, precision)

    add_mauritius_csg_component(
        salary_slip,
        "PRGF Employer",
        contribution,
        "employer_contributions",
    )


def is_mauritius_hrdc_age_eligible(salary_slip):
    date_of_birth = frappe.db.get_value(
        "Employee",
        salary_slip.employee,
        "date_of_birth",
    )

    if not date_of_birth:
        frappe.throw("Date of Birth is required to determine Mauritius HRDC Levy eligibility.")

    date_of_birth = getdate(date_of_birth)
    start_date = getdate(salary_slip.start_date)
    end_date = getdate(salary_slip.end_date)

    eighteenth_birthday = add_years(date_of_birth, 18)
    final_retirement_birthday = add_years(date_of_birth, 70)

    if end_date < eighteenth_birthday:
        return False

    if start_date >= final_retirement_birthday:
        return False

    if start_date < eighteenth_birthday <= end_date:
        frappe.throw(
            "Employee attains age 18 during this payroll period. Review HRDC Training Levy treatment for the transition month before processing payroll."
        )

    if start_date < final_retirement_birthday <= end_date:
        frappe.throw(
            "Employee attains final retirement age 70 during this payroll period. Review HRDC Training Levy treatment for the transition month before processing payroll."
        )

    return True


def get_mauritius_hrdc_base(salary_slip):
    total = 0
    for row in salary_slip.get("earnings", []):
        is_hrdc_base = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            "custom_mauritius_hrdc_levy_base",
        )
        if is_hrdc_base:
            total += flt(row.amount)
    return total


def apply_mauritius_hrdc_levy(salary_slip):
    hrdc_base = get_mauritius_hrdc_base(salary_slip)

    if hrdc_base <= 0 or not is_mauritius_hrdc_age_eligible(salary_slip):
        add_mauritius_csg_component(
            salary_slip, "HRDC Training Levy", 0, "employer_contributions"
        )
        return

    precision = frappe.get_precision("Salary Detail", "amount") or 2
    levy_amount = flt(hrdc_base * 0.015, precision)

    add_mauritius_csg_component(
        salary_slip,
        "HRDC Training Levy",
        levy_amount,
        "employer_contributions",
    )


def get_current_mauritius_fsc_taxable_emoluments(salary_slip):
    """
    Split current taxable earnings between normal emoluments
    and prescribed EOY bonus for Mauritius FSC processing.
    """

    normal_taxable = 0.0
    prescribed_eoy_bonus = 0.0

    for row in salary_slip.get("earnings", []):
        if not row.is_tax_applicable:
            continue

        treatment = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            "custom_mauritius_csg_treatment",
        )

        if treatment == "Prescribed EOY Bonus":
            prescribed_eoy_bonus += flt(row.amount)
        else:
            normal_taxable += flt(row.amount)

    return {
        "normal_taxable": normal_taxable,
        "prescribed_eoy_bonus": prescribed_eoy_bonus,
        "total_taxable": normal_taxable + prescribed_eoy_bonus,
    }


def get_previous_mauritius_fsc(salary_slip):
    """
    Return Fair Share Contribution already deducted on previous
    submitted Salary Slips in the current payroll period.
    """

    start_date = getdate(salary_slip.start_date)

    if start_date.month == 7:
        return 0.0

    period_start = getdate(
        salary_slip.payroll_period.start_date
    )

    previous_period_end = add_days(
        start_date,
        -1,
    )

    return salary_slip.get_salary_slip_details(
        period_start,
        previous_period_end,
        parentfield="deductions",
        salary_component="Fair Share Contribution",
    )


def calculate_mauritius_fsc_deduction(
    cumulative_chargeable_income,
    threshold,
    previous_fsc=0,
):
    """
    Calculate current-period Mauritius Fair Share Contribution.

    FSC is 15% of cumulative chargeable income above the
    applicable cumulative FSC threshold, less FSC already withheld.
    """

    cumulative_liability = math.floor(
        max(
            0,
            (flt(cumulative_chargeable_income) - flt(threshold)) * 0.15,
        )
    )

    return max(
        0,
        cumulative_liability - math.floor(flt(previous_fsc)),
    )


def get_mauritius_fsc_period_number(value):
    """
    Return the statutory FSC period for a normal payroll month.

    The prescribed EOY bonus is separate period 6.
    December regular emoluments are always period 7.
    """

    month = getdate(value).month

    periods = {
        7: 1,
        8: 2,
        9: 3,
        10: 4,
        11: 5,
        12: 7,
        1: 8,
        2: 9,
        3: 10,
        4: 11,
        5: 12,
        6: 13,
    }

    return periods.get(month)


def calculate_mauritius_fsc_for_salary_slip(salary_slip):
    """
    Calculate current Mauritius FSC withholding for a Salary Slip.

    Normal periods are calculated cumulatively.

    Where a December Salary Slip contains the prescribed EOY bonus,
    FSC is calculated in two statutory stages:
    period 6 - prescribed EOY bonus
    period 7 - December regular emoluments
    """

    split = get_current_mauritius_fsc_taxable_emoluments(
        salary_slip
    )

    previous_taxable = get_previous_taxable_emoluments(
        salary_slip
    )

    previous_fsc = get_previous_mauritius_fsc(
        salary_slip
    )

    start_date = getdate(salary_slip.start_date)

    normal_taxable = flt(split["normal_taxable"])
    prescribed_bonus = flt(split["prescribed_eoy_bonus"])
    total_taxable = flt(split["total_taxable"])

    # December containing the prescribed EOY bonus must preserve
    # the statutory bonus period before the December period.
    if start_date.month == 12 and prescribed_bonus > 0:
        bonus_cumulative_taxable = (
            previous_taxable
            + prescribed_bonus
        )

        bonus_cumulative_edf = get_cumulative_edf_relief(
            salary_slip,
            6,
        )

        bonus_chargeable = max(
            0,
            bonus_cumulative_taxable - bonus_cumulative_edf,
        )

        bonus_fsc = calculate_mauritius_fsc_deduction(
            bonus_chargeable,
            get_mauritius_fsc_threshold_for_period(6),
            previous_fsc,
        )

        fsc_after_bonus = previous_fsc + bonus_fsc

        december_cumulative_taxable = (
            previous_taxable
            + prescribed_bonus
            + normal_taxable
        )

        december_cumulative_edf = get_cumulative_edf_relief(
            salary_slip,
            7,
        )

        december_chargeable = max(
            0,
            december_cumulative_taxable
            - december_cumulative_edf,
        )

        december_fsc = calculate_mauritius_fsc_deduction(
            december_chargeable,
            get_mauritius_fsc_threshold_for_period(7),
            fsc_after_bonus,
        )

        return bonus_fsc + december_fsc

    period_number = get_mauritius_fsc_period_number(
        start_date
    )

    if not period_number:
        return 0.0

    cumulative_taxable = (
        previous_taxable
        + total_taxable
    )

    cumulative_edf = get_cumulative_edf_relief(
        salary_slip,
        period_number,
    )

    cumulative_chargeable = max(
        0,
        cumulative_taxable - cumulative_edf,
    )

    return calculate_mauritius_fsc_deduction(
        cumulative_chargeable,
        get_mauritius_fsc_threshold_for_period(
            period_number
        ),
        previous_fsc,
    )


def get_mauritius_fsc_threshold_for_period(period_number):
    """
    Return the published cumulative Mauritius FSC threshold
    for statutory periods 1 through 13.
    """

    thresholds = {
        1: 923077.0,
        2: 1846154.0,
        3: 2769231.0,
        4: 3692308.0,
        5: 4615385.0,
        6: 5538562.0,
        7: 6461538.0,
        8: 7384615.0,
        9: 8307692.0,
        10: 9230769.0,
        11: 10153846.0,
        12: 11076923.0,
        13: 12000000.0,
    }

    return thresholds.get(int(period_number or 0))


def get_mauritius_fsc_threshold(value, prescribed_eoy_bonus=False):
    """
    Return the published cumulative Mauritius FSC income threshold.

    The prescribed EOY bonus has its own threshold period.
    In the normal payroll workflow, where the EOY bonus is included
    together with the December Salary Slip, the December threshold applies.
    """

    if prescribed_eoy_bonus:
        return 5538562.0

    month = getdate(value).month

    thresholds = {
        7: 923077.0,
        8: 1846154.0,
        9: 2769231.0,
        10: 3692308.0,
        11: 4615385.0,
        12: 6461538.0,
        1: 7384615.0,
        2: 8307692.0,
        3: 9230769.0,
        4: 10153846.0,
        5: 11076923.0,
        6: 12000000.0,
    }

    return thresholds.get(month)


def get_mauritius_period_number(value):
    """
    Return the cumulative Mauritius monthly PAYE period number.

    December salary together with the prescribed EOY bonus
    brings the cumulative PAYE period number to 7.
    """

    month = getdate(value).month

    period_number_by_month = {
        7: 1,
        8: 2,
        9: 3,
        10: 4,
        11: 5,
        12: 6,
        1: 8,
        2: 9,
        3: 10,
        4: 11,
        5: 12,
        6: 13,
    }

    return period_number_by_month.get(month)


def get_mauritius_edf_start_period(value):
    """
    Return the first Mauritius PAYE period affected by
    an EDF effective date.

    December starts at period 6 because December salary
    is one PAYE period and the prescribed EOY bonus is
    the additional period 7.
    """

    month = getdate(value).month

    start_period_by_month = {
        7: 1,
        8: 2,
        9: 3,
        10: 4,
        11: 5,
        12: 6,
        1: 8,
        2: 9,
        3: 10,
        4: 11,
        5: 12,
        6: 13,
    }

    return start_period_by_month.get(month)


def get_edf_declaration_history(salary_slip):
    """
    Return the current submitted Mauritius EDF together with
    its amendment history, ordered from oldest to newest.
    """

    current_name = frappe.db.get_value(
        "Employee Tax Exemption Declaration",
        {
            "employee": salary_slip.employee,
            "payroll_period": salary_slip.payroll_period.name,
            "docstatus": 1,
        },
        "name",
    )

    if not current_name:
        return []

    history = []
    seen = set()
    declaration_name = current_name

    while declaration_name:
        if declaration_name in seen:
            frappe.throw(
                "Circular Employee Tax Exemption Declaration "
                "amendment chain detected."
            )

        seen.add(declaration_name)

        declaration = frappe.db.get_value(
            "Employee Tax Exemption Declaration",
            declaration_name,
            [
                "name",
                "amended_from",
                "total_exemption_amount",
                "custom_mauritius_edf_effective_from",
            ],
            as_dict=True,
        )

        if not declaration:
            break

        history.append(declaration)
        declaration_name = declaration.amended_from

    history.reverse()

    return history


def get_cumulative_edf_relief(salary_slip, period_number):
    """
    Calculate cumulative Mauritius EDF relief for the current
    PAYE period.

    For a fresh EDF during the income year, only the variance
    from the previous EDF is spread over the remaining PAYE
    periods from its effective month.
    """

    if not salary_slip.tax_slab.allow_tax_exemption:
        return 0.0

    # Any standard exemption configured on the Income Tax Slab
    # applies from the beginning of the income year.
    standard_exemption = flt(
        salary_slip.tax_slab.standard_tax_exemption_amount or 0
    )

    cumulative_relief = (
        standard_exemption
        * flt(period_number)
        / MRA_MONTHLY_PAYE_PERIODS
    )

    history = get_edf_declaration_history(salary_slip)

    previous_annual_amount = 0.0

    for declaration in history:
        annual_amount = flt(
            declaration.total_exemption_amount or 0
        )

        effective_date = (
            declaration.custom_mauritius_edf_effective_from
            or salary_slip.payroll_period.start_date
        )

        start_period = get_mauritius_edf_start_period(
            effective_date
        )

        if not start_period:
            previous_annual_amount = annual_amount
            continue

        variance = annual_amount - previous_annual_amount

        if period_number >= start_period:
            remaining_periods = (
                MRA_MONTHLY_PAYE_PERIODS
                - start_period
                + 1
            )

            elapsed_periods = (
                period_number
                - start_period
                + 1
            )

            cumulative_relief += (
                variance
                * flt(elapsed_periods)
                / flt(remaining_periods)
            )

        previous_annual_amount = annual_amount

    return max(0.0, cumulative_relief)


def get_annual_edf_relief(salary_slip):
    """
    Get Mauritius annual EDF relief directly from the submitted
    Employee Tax Exemption Declaration.

    Mauritius PAYE continues to use the employee's submitted EDF
    throughout the income year. We therefore do not use Frappe's
    year-end tax exemption proof switch.
    """

    if not salary_slip.tax_slab.allow_tax_exemption:
        return 0.0

    declaration_amount = frappe.db.get_value(
        "Employee Tax Exemption Declaration",
        {
            "employee": salary_slip.employee,
            "payroll_period": salary_slip.payroll_period.name,
            "docstatus": 1,
        },
        "total_exemption_amount",
    )

    annual_relief = flt(declaration_amount or 0)

    # Preserve any standard exemption configured on the Income Tax Slab.
    annual_relief += flt(
        salary_slip.tax_slab.standard_tax_exemption_amount or 0
    )

    return annual_relief

def get_income_tax_row(salary_slip):
    """
    Return the Salary Slip deduction row representing PAYE.

    Do not depend on the component being named PAYE or
    having a particular abbreviation.
    """

    for row in salary_slip.get("deductions"):
        component = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            [
                "variable_based_on_taxable_salary",
                "is_income_tax_component",
            ],
            as_dict=True,
        )

        if (
            component
            and component.variable_based_on_taxable_salary
            and component.is_income_tax_component
        ):
            return row

    return None


def get_current_taxable_emoluments(salary_slip):
    """
    Sum taxable earnings on the current Salary Slip.
    """

    taxable_emoluments = 0.0

    for row in salary_slip.get("earnings"):
        if row.is_tax_applicable:
            taxable_emoluments += flt(row.amount)

    return taxable_emoluments


def get_previous_taxable_emoluments(salary_slip):
    """
    Get taxable earnings from previous submitted Salary Slips
    in the same payroll period.
    """

    start_date = getdate(salary_slip.start_date)

    # July has no previous payroll period earnings.
    if start_date.month == 7:
        return 0.0

    period_start = getdate(
        salary_slip.payroll_period.start_date
    )

    previous_period_end = add_days(start_date, -1)

    return salary_slip.get_salary_slip_details(
        period_start,
        previous_period_end,
        parentfield="earnings",
        is_tax_applicable=1,
    )


def get_previous_paye(salary_slip, tax_component):
    """
    Get PAYE already deducted in previous submitted Salary Slips.
    """

    start_date = getdate(salary_slip.start_date)

    # July has no previous PAYE.
    if start_date.month == 7:
        return 0.0

    period_start = getdate(
        salary_slip.payroll_period.start_date
    )

    previous_period_end = add_days(start_date, -1)

    return salary_slip.get_tax_paid_in_period(
        period_start,
        previous_period_end,
        tax_component,
    )


def calculate_mauritius_cumulative_tax(
    taxable_emoluments,
    tax_slab,
    period_number,
):
    """
    Calculate cumulative Mauritius PAYE using the annual ERPNext
    Income Tax Slab prorated over 13 PAYE periods.
    """

    remaining_income = flt(taxable_emoluments)
    tax_amount = 0.0

    period_fraction = (
        flt(period_number)
        / MRA_MONTHLY_PAYE_PERIODS
    )

    slabs = sorted(
        tax_slab.slabs,
        key=lambda slab: flt(slab.from_amount),
    )

    for slab in slabs:
        if remaining_income <= 0:
            break

        from_amount = flt(slab.from_amount)
        to_amount = flt(slab.to_amount)
        rate = flt(slab.percent_deduction) / 100.0

        # Open-ended final tax band.
        if not to_amount:
            tax_amount += remaining_income * rate
            break

        # Convert ERPNext's inclusive slab limits into
        # the actual annual band width.
        annual_band_width = to_amount - from_amount

        if from_amount > 0:
            annual_band_width += 1

        cumulative_band_width = (
            annual_band_width * period_fraction
        )

        income_in_band = min(
            remaining_income,
            cumulative_band_width,
        )

        tax_amount += income_in_band * rate
        remaining_income -= income_in_band

    return tax_amount



def update_mauritius_income_tax_breakup(salary_slip, method=None):
    """
    Replace Frappe's displayed Income Tax Breakup values with
    Mauritius PAYE values.

    This runs after Salary Slip.validate(), so the actual PAYE
    deduction has already been calculated by apply_regional_deductions().
    """

    # Only apply to Mauritius companies.
    country = frappe.get_cached_value(
        "Company",
        salary_slip.company,
        "country",
    )

    if country != "Mauritius":
        return

    if not salary_slip.payroll_period:
        return

    # Salary Structure Assignment is prepared during normal
    # Salary Slip validation.
    if not hasattr(salary_slip, "_salary_structure_assignment"):
        salary_slip.set_salary_structure_assignment()

    tax_slab = getattr(salary_slip, "tax_slab", None)

    if not tax_slab:
        tax_slab = salary_slip.get_income_tax_slabs()

    salary_slip.tax_slab = tax_slab

    tax_row = get_income_tax_row(salary_slip)

    if not tax_row:
        return

    # -----------------------------------------------------
    # Mauritius annual EDF
    # -----------------------------------------------------

    annual_edf_relief = get_annual_edf_relief(salary_slip)

    standard_exemption = flt(
        tax_slab.standard_tax_exemption_amount or 0
    )

    salary_slip.standard_tax_exemption_amount = standard_exemption

    salary_slip.tax_exemption_declaration = max(
        0,
        annual_edf_relief - standard_exemption,
    )

    # -----------------------------------------------------
    # Annual taxable / chargeable income
    # -----------------------------------------------------

    total_earnings = flt(
        salary_slip.get("total_earnings") or 0
    )

    non_taxable_earnings = flt(
        salary_slip.get("non_taxable_earnings") or 0
    )

    deductions_before_tax = flt(
        salary_slip.get("deductions_before_tax_calculation") or 0
    )

    annual_chargeable_income = max(
        0,
        total_earnings
        - non_taxable_earnings
        - deductions_before_tax
        - annual_edf_relief,
    )

    salary_slip.annual_taxable_amount = annual_chargeable_income

    # -----------------------------------------------------
    # Full-year Mauritius tax liability
    # -----------------------------------------------------

    annual_tax = calculate_mauritius_cumulative_tax(
        taxable_emoluments=annual_chargeable_income,
        tax_slab=tax_slab,
        period_number=MRA_MONTHLY_PAYE_PERIODS,
    )

    annual_tax = math.floor(max(0, annual_tax))

    # -----------------------------------------------------
    # Actual cumulative PAYE
    # -----------------------------------------------------

    previous_paye = get_previous_paye(
        salary_slip,
        tax_row.salary_component,
    )

    current_paye = flt(tax_row.amount or 0)

    paye_deducted_till_date = (
        math.floor(previous_paye)
        + current_paye
    )

    salary_slip.current_month_income_tax = current_paye

    salary_slip.income_tax_deducted_till_date = (
        paye_deducted_till_date
    )

    salary_slip.total_income_tax = annual_tax

    salary_slip.future_income_tax_deductions = max(
        0,
        annual_tax - paye_deducted_till_date,
    )



def apply_mauritius_fsc(salary_slip):
    """
    Apply Mauritius Fair Share Contribution
    to Salary Slip deductions.
    """

    if not frappe.db.exists(
        "Salary Component",
        "Fair Share Contribution",
    ):
        frappe.throw(
            "Fair Share Contribution Salary Component is missing."
        )

    fsc_amount = calculate_mauritius_fsc_for_salary_slip(
        salary_slip
    )

    add_mauritius_csg_component(
        salary_slip,
        "Fair Share Contribution",
        fsc_amount,
        "deductions",
    )
