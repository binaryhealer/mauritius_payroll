from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    create_custom_fields(
        {
            "Additional Salary": [
                {
                    "fieldname": "custom_mauritius_eoy_generated",
                    "label": "Mauritius EOY Generated",
                    "fieldtype": "Check",
                    "default": "0",
                    "hidden": 1,
                    "read_only": 1,
                    "no_copy": 1,
                    "insert_after": "ref_docname",
                },
                {
                    "fieldname": "custom_mauritius_eoy_year",
                    "label": "Mauritius EOY Year",
                    "fieldtype": "Int",
                    "hidden": 1,
                    "read_only": 1,
                    "no_copy": 1,
                    "insert_after": "custom_mauritius_eoy_generated",
                },
            ]
        },
        update=True,
    )
