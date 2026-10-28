import frappe

from mauritius_payroll.payroll.eoy_bonus import (
    create_mauritius_eoy_bonus_bulk_drafts,
    preview_mauritius_eoy_bonus_bulk_generation,
    preview_mauritius_eoy_bonus_bulk_submission,
    submit_mauritius_eoy_bonus_bulk_drafts,
)


@frappe.whitelist()
def preview_eoy_bonus_generation(company, year, payroll_date):
    """
    Read-only API for Mauritius EOY bulk generation preview.

    Restricted to HR Manager.
    """

    frappe.only_for("HR Manager")

    if not company:
        frappe.throw("Company is required.")

    if not frappe.db.exists("Company", company):
        frappe.throw(f"Company {company} does not exist.")

    if not year:
        frappe.throw("Year is required.")

    if not payroll_date:
        frappe.throw("Payroll Date is required.")

    return preview_mauritius_eoy_bonus_bulk_generation(
        company,
        year,
        payroll_date,
    )

@frappe.whitelist()
def preview_eoy_bonus_submission(company, year):
    """
    Read-only API for Mauritius EOY bulk submission preview.

    Restricted to HR Manager.
    """

    frappe.only_for("HR Manager")

    if not company:
        frappe.throw("Company is required.")

    if not frappe.db.exists("Company", company):
        frappe.throw(f"Company {company} does not exist.")

    if not year:
        frappe.throw("Year is required.")

    return preview_mauritius_eoy_bonus_bulk_submission(
        company,
        year,
    )

@frappe.whitelist(methods=["POST"])
def generate_eoy_bonus_drafts(company, year, payroll_date):
    """
    Generate Draft Mauritius EOY Additional Salaries in bulk.

    POST only. Restricted to HR Manager.
    """

    frappe.only_for("HR Manager")

    if not company:
        frappe.throw("Company is required.")

    if not frappe.db.exists("Company", company):
        frappe.throw(f"Company {company} does not exist.")

    if not year:
        frappe.throw("Year is required.")

    if not payroll_date:
        frappe.throw("Payroll Date is required.")

    return create_mauritius_eoy_bonus_bulk_drafts(
        company,
        year,
        payroll_date,
    )

@frappe.whitelist(methods=["POST"])
def submit_eoy_bonus_drafts(company, year):
    """
    Submit Mauritius-generated EOY Additional Salary Drafts in bulk.

    POST only. Restricted to HR Manager.
    """

    frappe.only_for("HR Manager")

    if not company:
        frappe.throw("Company is required.")

    if not frappe.db.exists("Company", company):
        frappe.throw(f"Company {company} does not exist.")

    if not year:
        frappe.throw("Year is required.")

    return submit_mauritius_eoy_bonus_bulk_drafts(
        company,
        year,
    )
