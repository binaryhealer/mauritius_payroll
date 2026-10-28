import frappe
from frappe.utils import flt, getdate, get_last_day


EOY_QUALIFYING_FIELD = "custom_mauritius_eoy_bonus_qualifying_earning"


def is_employee_employed_at_year_end(employee, year):
    year_end = getdate(f"{int(year)}-12-31")

    data = frappe.db.get_value(
        "Employee",
        employee,
        [
            "date_of_joining",
            "contract_end_date",
            "relieving_date",
            "date_of_retirement",
        ],
        as_dict=True,
    )

    if not data:
        frappe.throw(f"Employee {employee} was not found.")

    if data.date_of_joining and getdate(data.date_of_joining) > year_end:
        return False

    for fieldname in ["contract_end_date", "relieving_date", "date_of_retirement"]:
        value = data.get(fieldname)
        if value and getdate(value) < year_end:
            return False

    return True


def get_mauritius_eoy_qualifying_earnings(employee, year):
    year = int(year)
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=[
            ["Salary Slip", "employee", "=", employee],
            ["Salary Slip", "docstatus", "=", 1],
            ["Salary Slip", "start_date", "<=", end_date],
            ["Salary Slip", "end_date", ">=", start_date],
        ],
        pluck="name",
    )

    total = 0

    for salary_slip_name in salary_slips:
        salary_slip = frappe.get_doc("Salary Slip", salary_slip_name)

        for row in salary_slip.get("earnings", []):
            qualifies = frappe.get_cached_value(
                "Salary Component",
                row.salary_component,
                EOY_QUALIFYING_FIELD,
            )

            if qualifies:
                total += flt(row.amount)

    return total


def get_mauritius_eoy_year_end_draft_salary_slip(employee, year):
    """
    Return the single Draft Salary Slip covering 31 December for an employee.

    A Draft is considered only when there is no submitted Salary Slip
    already covering 31 December.

    Multiple year-end Draft Salary Slips are treated as a data error.
    """

    year = int(year)
    year_end = getdate(f"{year}-12-31")

    submitted = frappe.get_all(
        "Salary Slip",
        filters=[
            ["Salary Slip", "employee", "=", employee],
            ["Salary Slip", "docstatus", "=", 1],
            ["Salary Slip", "start_date", "<=", year_end],
            ["Salary Slip", "end_date", ">=", year_end],
        ],
        pluck="name",
        limit=1,
    )

    if submitted:
        return None

    drafts = frappe.get_all(
        "Salary Slip",
        filters=[
            ["Salary Slip", "employee", "=", employee],
            ["Salary Slip", "docstatus", "=", 0],
            ["Salary Slip", "start_date", "<=", year_end],
            ["Salary Slip", "end_date", ">=", year_end],
        ],
        pluck="name",
    )

    if len(drafts) > 1:
        frappe.throw(
            "Multiple Draft Salary Slips cover 31 December. "
            "Keep only one year-end Draft Salary Slip before EOY processing.",
            frappe.ValidationError,
        )

    return drafts[0] if drafts else None


def get_mauritius_eoy_year_end_draft_qualifying_earnings(employee, year):
    """
    Return EOY-qualifying earnings from the single valid year-end Draft
    Salary Slip, if one exists.

    Submitted Salary Slips remain the normal source of qualifying earnings.
    This helper is only for the controlled year-end Draft workflow.
    """

    draft_salary_slip = get_mauritius_eoy_year_end_draft_salary_slip(
        employee,
        year,
    )

    if not draft_salary_slip:
        return 0.0

    salary_slip = frappe.get_doc(
        "Salary Slip",
        draft_salary_slip,
    )

    total = 0.0

    for row in salary_slip.get("earnings", []):
        qualifies = frappe.get_cached_value(
            "Salary Component",
            row.salary_component,
            EOY_QUALIFYING_FIELD,
        )

        if qualifies:
            total += flt(row.amount)

    return total


def get_mauritius_eoy_preview_qualifying_earnings(employee, year):
    """
    Return qualifying earnings for EOY preview.

    Normal submitted Salary Slips remain authoritative.
    If no submitted Salary Slip covers 31 December, one valid
    year-end Draft Salary Slip may contribute its qualifying earnings.
    """

    submitted_earnings = get_mauritius_eoy_qualifying_earnings(
        employee,
        year,
    )

    draft_earnings = (
        get_mauritius_eoy_year_end_draft_qualifying_earnings(
            employee,
            year,
        )
    )

    return flt(submitted_earnings + draft_earnings)


def get_mauritius_eoy_monthly_basic_salary(employee, year):
    year_end = f"{int(year)}-12-31"

    assignments = frappe.get_all(
        "Salary Structure Assignment",
        filters={
            "employee": employee,
            "docstatus": 1,
            "from_date": ["<=", year_end],
        },
        fields=["base"],
        order_by="from_date desc",
        limit=1,
    )

    if not assignments:
        frappe.throw(
            "A submitted Salary Structure Assignment is required to determine the Mauritius EOY bonus regime."
        )

    return flt(assignments[0].base)


def get_mauritius_eoy_regime(employee, year):
    monthly_basic_salary = get_mauritius_eoy_monthly_basic_salary(employee, year)

    if monthly_basic_salary <= 100000:
        return "Workers Rights Act"

    return "End of Year Gratuity Act"


def get_mauritius_eoy_months_in_service(employee, year):
    year = int(year)
    year_start = getdate(f"{year}-01-01")
    year_end = getdate(f"{year}-12-31")

    data = frappe.db.get_value(
        "Employee",
        employee,
        ["date_of_joining", "contract_end_date", "relieving_date", "date_of_retirement"],
        as_dict=True,
    )

    if not data or not data.date_of_joining:
        frappe.throw("Date of Joining is required to calculate Mauritius End of Year Gratuity.")

    service_start = max(getdate(data.date_of_joining), year_start)
    service_end = year_end

    for fieldname in ["contract_end_date", "relieving_date", "date_of_retirement"]:
        value = data.get(fieldname)
        if value:
            service_end = min(service_end, getdate(value))

    if service_start > service_end:
        return 0

    if service_start > year_start and service_start.day != 1:
        frappe.throw(
            "Employee joined partway through a month. Review End of Year Gratuity month-count treatment before processing."
        )

    if service_end < year_end and service_end != get_last_day(service_end):
        frappe.throw(
            "Employee left partway through a month. Review End of Year Gratuity month-count treatment before processing."
        )

    return ((service_end.year - service_start.year) * 12) + service_end.month - service_start.month + 1


def calculate_mauritius_eoy_gratuity(employee, year):
    if not is_employee_employed_at_year_end(employee, year):
        frappe.throw(
            "This gratuity calculation currently supports employees still employed at 31 December only."
        )

    monthly_basic_salary = get_mauritius_eoy_monthly_basic_salary(employee, year)
    months_in_service = get_mauritius_eoy_months_in_service(employee, year)
    precision = frappe.get_precision("Salary Detail", "amount") or 2

    return flt(monthly_basic_salary * months_in_service / 12, precision)


def calculate_mauritius_statutory_eoy_bonus(employee, year):
    qualifying_earnings = get_mauritius_eoy_qualifying_earnings(employee, year)
    precision = frappe.get_precision("Salary Detail", "amount") or 2
    return flt(qualifying_earnings / 12, precision)


EOY_BONUS_COMPONENT = "Statutory EOY Bonus"


def get_mauritius_eoy_bonus_already_paid(employee, year):
    year = int(year)
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=[
            ["Salary Slip", "employee", "=", employee],
            ["Salary Slip", "docstatus", "=", 1],
            ["Salary Slip", "start_date", "<=", end_date],
            ["Salary Slip", "end_date", ">=", start_date],
        ],
        pluck="name",
    )

    total = 0

    for salary_slip_name in salary_slips:
        salary_slip = frappe.get_doc("Salary Slip", salary_slip_name)
        for row in salary_slip.get("earnings", []):
            if row.salary_component == EOY_BONUS_COMPONENT:
                total += flt(row.amount)

    return total


def get_mauritius_eoy_bonus_pending_additional_salary(employee, year):
    """
    Sum active EOY Bonus Additional Salary records for the year
    that have not yet been included in a submitted Salary Slip.
    """

    year = int(year)
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    additional_salaries = frappe.get_all(
        "Additional Salary",
        filters=[
            ["Additional Salary", "employee", "=", employee],
            ["Additional Salary", "salary_component", "=", EOY_BONUS_COMPONENT],
            ["Additional Salary", "docstatus", "!=", 2],
            ["Additional Salary", "disabled", "=", 0],
            ["Additional Salary", "is_recurring", "=", 0],
            ["Additional Salary", "payroll_date", "between", [start_date, end_date]],
        ],
        fields=["name", "amount"],
    )

    if not additional_salaries:
        return 0.0

    additional_salary_names = [
        d.name for d in additional_salaries
    ]

    salary_slips = frappe.get_all(
        "Salary Slip",
        filters=[
            ["Salary Slip", "employee", "=", employee],
            ["Salary Slip", "docstatus", "=", 1],
            ["Salary Slip", "start_date", "<=", end_date],
            ["Salary Slip", "end_date", ">=", start_date],
        ],
        pluck="name",
    )

    consumed_additional_salaries = set()

    if salary_slips:
        consumed_additional_salaries = set(
            frappe.get_all(
                "Salary Detail",
                filters=[
                    ["Salary Detail", "parenttype", "=", "Salary Slip"],
                    ["Salary Detail", "parentfield", "=", "earnings"],
                    ["Salary Detail", "parent", "in", salary_slips],
                    ["Salary Detail", "salary_component", "=", EOY_BONUS_COMPONENT],
                    ["Salary Detail", "additional_salary", "in", additional_salary_names],
                ],
                pluck="additional_salary",
            )
        )

    return sum(
        flt(d.amount)
        for d in additional_salaries
        if d.name not in consumed_additional_salaries
    )


def preview_mauritius_statutory_eoy_bonus(employee, year):
    precision = frappe.get_precision("Salary Detail", "amount") or 2
    qualifying_earnings = get_mauritius_eoy_preview_qualifying_earnings(
        employee,
        year,
    )
    regime = get_mauritius_eoy_regime(employee, year)
    already_paid = get_mauritius_eoy_bonus_already_paid(employee, year)
    pending_additional_salary = get_mauritius_eoy_bonus_pending_additional_salary(
        employee,
        year,
    )
    employed_at_year_end = is_employee_employed_at_year_end(employee, year)

    if not employed_at_year_end:
        processing_status = "Manual Review - Exit Case"
        entitlement = None
        balance_due = None
        available_to_generate = None
        excess_paid = None
    elif regime == "Workers Rights Act":
        processing_status = "Ready"
        entitlement = flt(qualifying_earnings / 12, precision)
        balance_due = flt(max(entitlement - already_paid, 0), precision)
        available_to_generate = flt(
            max(entitlement - already_paid - pending_additional_salary, 0),
            precision,
        )
        excess_paid = flt(max(already_paid - entitlement, 0), precision)

        if excess_paid > 0:
            processing_status = "Manual Review - EOY Already Overpaid"
        elif pending_additional_salary > balance_due:
            processing_status = "Manual Review - Pending EOY Exceeds Balance"
    elif regime == "End of Year Gratuity Act":
        processing_status = "Ready"
        entitlement = calculate_mauritius_eoy_gratuity(employee, year)
        balance_due = flt(max(entitlement - already_paid, 0), precision)
        available_to_generate = flt(
            max(entitlement - already_paid - pending_additional_salary, 0),
            precision,
        )
        excess_paid = flt(max(already_paid - entitlement, 0), precision)

        if excess_paid > 0:
            processing_status = "Manual Review - EOY Already Overpaid"
        elif pending_additional_salary > balance_due:
            processing_status = "Manual Review - Pending EOY Exceeds Balance"
    else:
        processing_status = "Manual Review"
        entitlement = None
        balance_due = None
        available_to_generate = None
        excess_paid = None

    return {
        "employee": employee,
        "year": int(year),
        "employed_at_year_end": employed_at_year_end,
        "regime": regime,
        "processing_status": processing_status,
        "qualifying_earnings": qualifying_earnings,
        "entitlement": entitlement,
        "already_paid": already_paid,
        "pending_additional_salary": pending_additional_salary,
        "balance_due": balance_due,
        "available_to_generate": available_to_generate,
        "excess_paid": excess_paid,
    }



def preview_mauritius_eoy_bonus_company(company, year):
    year = int(year)
    year_start = getdate(f"{year}-01-01")
    year_end = getdate(f"{year}-12-31")

    employees = frappe.get_all(
        "Employee",
        filters={"company": company},
        fields=[
            "name",
            "employee_name",
            "date_of_joining",
            "relieving_date",
        ],
        order_by="name",
    )

    results = []

    for employee in employees:
        if employee.date_of_joining and getdate(employee.date_of_joining) > year_end:
            continue

        if employee.relieving_date and getdate(employee.relieving_date) < year_start:
            continue

        salary_slips = frappe.get_all(
            "Salary Slip",
            filters={
                "employee": employee.name,
                "docstatus": 1,
                "start_date": ["between", [year_start, year_end]],
            },
            fields=["start_date"],
        )

        actual_payroll_months = sorted({
            getdate(d.start_date).strftime("%Y-%m")
            for d in salary_slips
        })

        year_end_draft_salary_slip = None

        try:
            year_end_draft_salary_slip = (
                get_mauritius_eoy_year_end_draft_salary_slip(
                    employee.name,
                    year,
                )
            )

            if year_end_draft_salary_slip:
                year_end_month = year_end.strftime("%Y-%m")

                if year_end_month not in actual_payroll_months:
                    actual_payroll_months.append(year_end_month)
                    actual_payroll_months.sort()

            expected_payroll_months = get_mauritius_eoy_months_in_service(
                employee.name,
                year,
            )

            service_start = max(getdate(employee.date_of_joining), year_start)
            start_month_index = service_start.year * 12 + service_start.month - 1

            expected_month_list = [
                f"{(start_month_index + offset) // 12:04d}-{((start_month_index + offset) % 12) + 1:02d}"
                for offset in range(expected_payroll_months)
            ]

            missing_payroll_months = [
                month
                for month in expected_month_list
                if month not in actual_payroll_months
            ]

            row = preview_mauritius_statutory_eoy_bonus(employee.name, year)
            row["employee_name"] = employee.employee_name
            row["salary_slip_count"] = (
                len(salary_slips)
                + (1 if year_end_draft_salary_slip else 0)
            )
            row["actual_payroll_months"] = len(actual_payroll_months)
            row["expected_payroll_months"] = expected_payroll_months
            row["missing_payroll_months"] = missing_payroll_months

            if missing_payroll_months:
                row["processing_status"] = "Manual Review - Incomplete Payroll History"
                row["entitlement"] = None
                row["balance_due"] = None
                row["available_to_generate"] = None
                row["excess_paid"] = None
        except frappe.ValidationError as exc:
            row = {
                "employee": employee.name,
                "employee_name": employee.employee_name,
                "year": year,
                "processing_status": "Manual Review - Data Error",
                "salary_slip_count": len(salary_slips),
                "actual_payroll_months": len(actual_payroll_months),
                "error": str(exc),
            }

        results.append(row)

    return results

def prepare_mauritius_eoy_bonus_additional_salary(employee, year, payroll_date):
    """
    Prepare the values for a Mauritius statutory EOY bonus Additional Salary.

    This function is read-only. It does not insert or submit any document.
    """

    year = int(year)
    payroll_date = getdate(payroll_date)

    if payroll_date.year != year:
        frappe.throw(
            f"Payroll Date {payroll_date} must fall within EOY year {year}."
        )

    company = frappe.db.get_value("Employee", employee, "company")

    if not company:
        frappe.throw(f"Employee {employee} was not found or has no Company.")

    preview_rows = preview_mauritius_eoy_bonus_company(company, year)

    preview = next(
        (row for row in preview_rows if row.get("employee") == employee),
        None,
    )

    if not preview:
        frappe.throw(
            f"Employee {employee} is not eligible for EOY processing for {year}."
        )

    if preview.get("processing_status") != "Ready":
        frappe.throw(
            f"EOY bonus cannot be prepared for {employee}: "
            f"{preview.get('processing_status')}."
        )

    amount = flt(preview.get("available_to_generate") or 0)

    if amount <= 0:
        frappe.throw(
            f"No EOY bonus amount is available to generate for {employee}."
        )

    return {
        "doctype": "Additional Salary",
        "employee": employee,
        "company": company,
        "salary_component": EOY_BONUS_COMPONENT,
        "payroll_date": payroll_date,
        "amount": amount,
        "is_recurring": 0,
        "overwrite_salary_structure_amount": 0,
        "deduct_full_tax_on_selected_payroll_date": 0,
        "custom_mauritius_eoy_generated": 1,
        "custom_mauritius_eoy_year": year,
        "preview": preview,
    }

def create_mauritius_eoy_bonus_additional_salary(employee, year, payroll_date):
    """
    Create one Draft Additional Salary for the Mauritius statutory EOY bonus.

    The document is inserted as Draft only. It is not submitted.
    """

    prepared = prepare_mauritius_eoy_bonus_additional_salary(
        employee,
        year,
        payroll_date,
    )

    values = {
        key: value
        for key, value in prepared.items()
        if key != "preview"
    }

    doc = frappe.get_doc(values)
    doc.insert()

    return {
        "name": doc.name,
        "docstatus": doc.docstatus,
        "employee": doc.employee,
        "company": doc.company,
        "salary_component": doc.salary_component,
        "payroll_date": doc.payroll_date,
        "amount": flt(doc.amount),
    }

def validate_mauritius_eoy_bonus_additional_salary_for_submission(
    additional_salary,
    year=None,
):
    """
    Validate one Draft Additional Salary before Mauritius EOY submission.

    This function is read-only. It does not save or submit the document.
    """

    doc = frappe.get_doc("Additional Salary", additional_salary)

    if doc.docstatus != 0:
        frappe.throw(
            f"Additional Salary {doc.name} must be in Draft status."
        )

    if int(doc.get("custom_mauritius_eoy_generated") or 0) != 1:
        frappe.throw(
            f"Additional Salary {doc.name} was not generated by "
            "the Mauritius EOY process."
        )

    eoy_year = int(doc.get("custom_mauritius_eoy_year") or 0)

    if not eoy_year:
        frappe.throw(
            f"Additional Salary {doc.name} has no Mauritius EOY year."
        )

    if year is not None and eoy_year != int(year):
        frappe.throw(
            f"Additional Salary {doc.name} belongs to EOY year "
            f"{eoy_year}, not {int(year)}."
        )

    if doc.salary_component != EOY_BONUS_COMPONENT:
        frappe.throw(
            f"Additional Salary {doc.name} does not use "
            f"{EOY_BONUS_COMPONENT}."
        )

    payroll_date = getdate(doc.payroll_date)

    if payroll_date.year != eoy_year:
        frappe.throw(
            f"Payroll Date {payroll_date} does not match "
            f"EOY year {eoy_year}."
        )

    if int(doc.get("is_recurring") or 0):
        frappe.throw(
            f"Additional Salary {doc.name} must be non-recurring."
        )

    if int(doc.get("disabled") or 0):
        frappe.throw(
            f"Additional Salary {doc.name} is disabled."
        )

    if flt(doc.amount) <= 0:
        frappe.throw(
            f"Additional Salary {doc.name} must have a positive amount."
        )

    employee_company = frappe.db.get_value(
        "Employee",
        doc.employee,
        "company",
    )

    if not employee_company or employee_company != doc.company:
        frappe.throw(
            f"Employee {doc.employee} does not match company {doc.company}."
        )

    preview_rows = preview_mauritius_eoy_bonus_company(
        doc.company,
        eoy_year,
    )

    preview = next(
        (
            row
            for row in preview_rows
            if row.get("employee") == doc.employee
        ),
        None,
    )

    if not preview:
        frappe.throw(
            f"Employee {doc.employee} is not eligible for "
            f"EOY processing for {eoy_year}."
        )

    if preview.get("processing_status") != "Ready":
        frappe.throw(
            f"EOY Additional Salary {doc.name} cannot be submitted: "
            f"{preview.get('processing_status')}."
        )

    return {
        "name": doc.name,
        "employee": doc.employee,
        "company": doc.company,
        "year": eoy_year,
        "payroll_date": payroll_date,
        "amount": flt(doc.amount),
        "processing_status": preview.get("processing_status"),
        "balance_due": preview.get("balance_due"),
        "pending_additional_salary": preview.get(
            "pending_additional_salary"
        ),
    }

def refresh_mauritius_eoy_year_end_draft_salary_slip(employee, year):
    """
    Rebuild the single valid year-end Draft Salary Slip, if one exists.

    This uses HRMS's native Salary Slip rebuild path so newly submitted
    Additional Salary records are pulled into the existing December Draft.
    """

    draft_salary_slip = get_mauritius_eoy_year_end_draft_salary_slip(
        employee,
        year,
    )

    if not draft_salary_slip:
        return {
            "refreshed": False,
            "salary_slip": None,
        }

    salary_slip = frappe.get_doc(
        "Salary Slip",
        draft_salary_slip,
    )

    salary_slip.get_emp_and_working_day_details()
    salary_slip.save(ignore_permissions=True)

    return {
        "refreshed": True,
        "salary_slip": salary_slip.name,
    }


def submit_mauritius_eoy_bonus_additional_salary(
    additional_salary,
    year,
):
    """
    Validate and submit one Mauritius EOY Additional Salary.
    """

    validated = validate_mauritius_eoy_bonus_additional_salary_for_submission(
        additional_salary,
        year,
    )

    doc = frappe.get_doc("Additional Salary", validated["name"])
    doc.submit()

    refresh_result = (
        refresh_mauritius_eoy_year_end_draft_salary_slip(
            doc.employee,
            year,
        )
    )

    return {
        "name": doc.name,
        "docstatus": doc.docstatus,
        "employee": doc.employee,
        "company": doc.company,
        "year": int(doc.custom_mauritius_eoy_year),
        "salary_component": doc.salary_component,
        "payroll_date": getdate(doc.payroll_date),
        "amount": flt(doc.amount),
        "year_end_draft_refreshed": refresh_result.get("refreshed"),
        "year_end_draft_salary_slip": refresh_result.get("salary_slip"),
    }

def preview_mauritius_eoy_bonus_bulk_generation(
    company,
    year,
    payroll_date,
):
    """
    Preview bulk Mauritius EOY bonus generation for a company.

    This function is read-only. It does not create or submit
    any Additional Salary documents.
    """

    year = int(year)
    payroll_date = getdate(payroll_date)

    if payroll_date.year != year:
        frappe.throw(
            f"Payroll Date {payroll_date} must fall within "
            f"EOY year {year}."
        )

    preview_rows = preview_mauritius_eoy_bonus_company(
        company,
        year,
    )

    results = []

    for row in preview_rows:
        result = dict(row)
        result["payroll_date"] = payroll_date

        processing_status = row.get("processing_status")
        available = row.get("available_to_generate")

        if processing_status != "Ready":
            result["bulk_status"] = "Skipped / Manual Review"

        elif flt(available or 0) <= 0:
            result["bulk_status"] = "Nothing to Generate"

        else:
            result["bulk_status"] = "Ready to Generate"

        results.append(result)

    return results

def create_mauritius_eoy_bonus_bulk_drafts(
    company,
    year,
    payroll_date,
):
    """
    Create Draft Mauritius EOY Additional Salary records in bulk.

    Only employees classified as Ready to Generate are processed.
    Documents are created as Draft only and are not submitted.
    """

    year = int(year)
    payroll_date = getdate(payroll_date)

    preview_rows = preview_mauritius_eoy_bonus_bulk_generation(
        company,
        year,
        payroll_date,
    )

    results = []

    for row in preview_rows:
        result = {
            "employee": row.get("employee"),
            "employee_name": row.get("employee_name"),
            "processing_status": row.get("processing_status"),
            "bulk_status": row.get("bulk_status"),
            "available_to_generate": row.get(
                "available_to_generate"
            ),
            "payroll_date": payroll_date,
            "additional_salary": None,
        }

        if row.get("bulk_status") != "Ready to Generate":
            result["generation_status"] = "Skipped"
            results.append(result)
            continue

        try:
            created = create_mauritius_eoy_bonus_additional_salary(
                row.get("employee"),
                year,
                payroll_date,
            )

            result["generation_status"] = "Draft Created"
            result["additional_salary"] = created.get("name")
            result["amount"] = created.get("amount")

        except frappe.ValidationError as exc:
            result["generation_status"] = "Validation Error"
            result["error"] = str(exc)

        results.append(result)

    return results

def preview_mauritius_eoy_bonus_bulk_submission(
    company,
    year,
):
    """
    Preview Mauritius EOY generated Drafts for bulk submission.

    This function is read-only. It does not save or submit
    any Additional Salary documents.
    """

    year = int(year)

    drafts = frappe.get_all(
        "Additional Salary",
        filters={
            "company": company,
            "docstatus": 0,
            "custom_mauritius_eoy_generated": 1,
            "custom_mauritius_eoy_year": year,
        },
        fields=[
            "name",
            "employee",
            "salary_component",
            "payroll_date",
            "amount",
        ],
        order_by="employee, name",
    )

    results = []

    for draft in drafts:
        result = {
            "additional_salary": draft.name,
            "employee": draft.employee,
            "company": company,
            "year": year,
            "salary_component": draft.salary_component,
            "payroll_date": getdate(draft.payroll_date),
            "amount": flt(draft.amount),
        }

        try:
            validated = (
                validate_mauritius_eoy_bonus_additional_salary_for_submission(
                    draft.name,
                    year,
                )
            )

            result["submission_status"] = "Ready to Submit"
            result["processing_status"] = validated.get(
                "processing_status"
            )
            result["balance_due"] = validated.get("balance_due")
            result["pending_additional_salary"] = validated.get(
                "pending_additional_salary"
            )

        except frappe.ValidationError as exc:
            result["submission_status"] = (
                "Manual Review / Validation Error"
            )
            result["error"] = str(exc)

        results.append(result)

    return results

def submit_mauritius_eoy_bonus_bulk_drafts(
    company,
    year,
):
    """
    Submit Mauritius-generated EOY Additional Salary Drafts in bulk.

    Only Drafts classified as Ready to Submit are processed.
    Each Draft is revalidated immediately before submission.
    """

    year = int(year)

    preview_rows = preview_mauritius_eoy_bonus_bulk_submission(
        company,
        year,
    )

    results = []

    for row in preview_rows:
        result = {
            "additional_salary": row.get("additional_salary"),
            "employee": row.get("employee"),
            "company": company,
            "year": year,
            "amount": row.get("amount"),
            "submission_status": row.get("submission_status"),
        }

        if row.get("submission_status") != "Ready to Submit":
            result["bulk_submission_status"] = "Skipped"
            result["error"] = row.get("error")
            results.append(result)
            continue

        try:
            submitted = submit_mauritius_eoy_bonus_additional_salary(
                row.get("additional_salary"),
                year,
            )

            result["bulk_submission_status"] = "Submitted"
            result["docstatus"] = submitted.get("docstatus")
            result["amount"] = submitted.get("amount")

        except frappe.ValidationError as exc:
            result["bulk_submission_status"] = "Validation Error"
            result["error"] = str(exc)

        results.append(result)

    return results
