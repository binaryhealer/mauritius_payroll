import frappe


STATUTORY_SALARY_COMPONENTS = {
    "PAYE": {
        "type": "Deduction",
        "salary_component_abbr": "IT",
        "description": "Income Tax",
        "is_income_tax_component": 1,
        "is_tax_applicable": 1,
        "variable_based_on_taxable_salary": 1,
        "remove_if_zero_valued": 1,
    },
    "CSG Employee": {
        "type": "Deduction",
        "salary_component_abbr": "CSGEE",
        "description": "CSG Employee",
        "remove_if_zero_valued": 1,
    },
    "CSG Employer": {
        "type": "Employer Contribution",
        "salary_component_abbr": "CSGER",
        "description": "CSG Employer",
        "is_tax_applicable": 1,
        "remove_if_zero_valued": 1,
    },
    "CSG Employee - EOY Bonus": {
        "type": "Deduction",
        "salary_component_abbr": "CSGEEB",
        "description": "CSG Employee - EOY Bonus",
        "remove_if_zero_valued": 1,
    },
    "CSG Employer - EOY Bonus": {
        "type": "Employer Contribution",
        "salary_component_abbr": "CSGERB",
        "description": "CSG Employer - EOY Bonus",
        "remove_if_zero_valued": 1,
    },
    "NSF Employee": {
        "type": "Deduction",
        "salary_component_abbr": "NSFEE",
        "description": "NSF Employee",
        "remove_if_zero_valued": 1,
    },
    "NSF Employer": {
        "type": "Employer Contribution",
        "salary_component_abbr": "NSFER",
        "description": "NSF Employer",
        "remove_if_zero_valued": 1,
    },
    "HRDC Training Levy": {
        "type": "Employer Contribution",
        "salary_component_abbr": "HRDC",
        "description": "HRDC Training Levy",
        "is_tax_applicable": 1,
        "remove_if_zero_valued": 1,
    },
    "PRGF Employer": {
        "type": "Employer Contribution",
        "salary_component_abbr": "PRGF",
        "description": "PRGF Employer",
        "is_tax_applicable": 1,
        "remove_if_zero_valued": 1,
    },
    "Fair Share Contribution": {
        "type": "Deduction",
        "salary_component_abbr": "FSC",
        "is_tax_applicable": 1,
        "remove_if_zero_valued": 1,
    },
    "Statutory EOY Bonus": {
        "type": "Earning",
        "salary_component_abbr": "EOYB",
        "description": "Statutory EOY Bonus",
        "is_tax_applicable": 1,
        "remove_if_zero_valued": 1,
        "custom_mauritius_csg_treatment": "Prescribed EOY Bonus",
    },
}


def ensure_statutory_salary_components():
    """Create or update Mauritius statutory Salary Components.

    Existing company-specific account mappings are intentionally preserved.
    """
    for component_name, values in STATUTORY_SALARY_COMPONENTS.items():
        if frappe.db.exists("Salary Component", component_name):
            doc = frappe.get_doc("Salary Component", component_name)

            changed = False

            for fieldname, value in values.items():
                if doc.get(fieldname) != value:
                    doc.set(fieldname, value)
                    changed = True

            if changed:
                doc.save(ignore_permissions=True)

        else:
            doc = frappe.get_doc(
                {
                    "doctype": "Salary Component",
                    "salary_component": component_name,
                    **values,
                }
            )
            doc.insert(ignore_permissions=True)
