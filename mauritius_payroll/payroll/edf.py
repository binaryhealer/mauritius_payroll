import frappe
from frappe import _
from frappe.utils import getdate


DEPENDENTS_CATEGORY = "Mauritius EDF - Dependents"
MEDICAL_CATEGORY = "Mauritius EDF - Medical Insurance"
TERTIARY_CATEGORY = "Mauritius EDF - Tertiary Education"
PRIVATE_SCHOOL_CATEGORY = "Mauritius EDF - Private School Fees"

PRIVATE_SCHOOL_CHILDREN = [
    "Private School Fees - Child 1",
    "Private School Fees - Child 2",
    "Private School Fees - Child 3",
    "Private School Fees - Child 4",
]


DEPENDENT_TIERS = {
    "1 Dependent": 1,
    "2 Dependents": 2,
    "3 Dependents": 3,
    "4 or More Dependents": 4,
}


MEDICAL_SELF = "Medical Insurance - Self"

MEDICAL_DEPENDENTS = [
    "Medical Insurance - First Dependent",
    "Medical Insurance - Second Dependent",
    "Medical Insurance - Third Dependent",
    "Medical Insurance - Fourth Dependent",
]


def validate_edf_declaration(doc, method=None):
    """
    Mauritius EDF validation rules.
    """

    country = frappe.get_cached_value(
        "Company",
        doc.company,
        "country",
    )

    if country != "Mauritius":
        return

    # -----------------------------------------------------
    # Mauritius EDF Effective Date
    # -----------------------------------------------------

    if not doc.custom_mauritius_edf_effective_from:
        frappe.throw(
            _(
                "Mauritius EDF Effective From is required."
            ),
            title=_("Missing EDF Effective Date"),
        )

    effective_date = getdate(
        doc.custom_mauritius_edf_effective_from
    )

    payroll_period = frappe.db.get_value(
        "Payroll Period",
        doc.payroll_period,
        [
            "start_date",
            "end_date",
        ],
        as_dict=True,
    )

    if not payroll_period:
        frappe.throw(
            _("Payroll Period could not be found.")
        )

    period_start = getdate(
        payroll_period.start_date
    )

    period_end = getdate(
        payroll_period.end_date
    )

    if not (
        period_start
        <= effective_date
        <= period_end
    ):
        frappe.throw(
            _(
                "Mauritius EDF Effective From must fall "
                "within the selected Payroll Period."
            ),
            title=_("Invalid EDF Effective Date"),
        )

    # Mauritius Payroll currently supports monthly PAYE.
    # Use the first day of the month as the effective
    # payroll-period marker.
    if effective_date.day != 1:
        frappe.throw(
            _(
                "Mauritius EDF Effective From must be "
                "the first day of a month."
            ),
            title=_("Invalid EDF Effective Date"),
        )

    # An amended EDF must apply after the EDF it replaces.
    amended_from = doc.get("amended_from")

    if amended_from:
        previous_effective_date = frappe.db.get_value(
            "Employee Tax Exemption Declaration",
            amended_from,
            "custom_mauritius_edf_effective_from",
        )

        if previous_effective_date:
            previous_effective_date = getdate(
                previous_effective_date
            )

            if effective_date <= previous_effective_date:
                frappe.throw(
                    _(
                        "An amended Mauritius EDF must have an "
                        "Effective From date later than the EDF "
                        "it replaces."
                    ),
                    title=_("Invalid EDF Amendment Date"),
                )

    declarations = doc.declarations or []

    # -----------------------------------------------------
    # Dependents
    # -----------------------------------------------------

    dependent_rows = [
        row
        for row in declarations
        if row.exemption_category == DEPENDENTS_CATEGORY
    ]

    if len(dependent_rows) > 1:
        frappe.throw(
            _(
                "Only one dependent tier may be selected in a Mauritius EDF. "
                "Choose either 1 Dependent, 2 Dependents, 3 Dependents, "
                "or 4 or More Dependents."
            ),
            title=_("Invalid Dependent Declaration"),
        )

    dependent_count = 0

    if dependent_rows:
        dependent_tier = dependent_rows[0].exemption_sub_category

        dependent_count = DEPENDENT_TIERS.get(
            dependent_tier,
            0,
        )

    # -----------------------------------------------------
    # Medical Insurance
    # -----------------------------------------------------

    medical_rows = [
        row
        for row in declarations
        if row.exemption_category == MEDICAL_CATEGORY
    ]

    # Prevent duplicate medical insurance subcategories.
    seen_medical = set()

    for row in medical_rows:
        subcategory = row.exemption_sub_category

        if subcategory in seen_medical:
            frappe.throw(
                _(
                    "Medical insurance category '{0}' "
                    "may only be entered once."
                ).format(subcategory),
                title=_("Duplicate Medical Insurance Declaration"),
            )

        seen_medical.add(subcategory)

    # Self is always potentially available.
    allowed_medical = {MEDICAL_SELF}

    # Add medical dependent rows according to the
    # number of dependents declared.
    for index in range(dependent_count):
        allowed_medical.add(MEDICAL_DEPENDENTS[index])

    invalid_medical = [
        row.exemption_sub_category
        for row in medical_rows
        if row.exemption_sub_category not in allowed_medical
    ]

    if invalid_medical:
        frappe.throw(
            _(
                "The following medical insurance declaration is not "
                "allowed for the selected dependent tier: {0}"
            ).format(", ".join(invalid_medical)),
            title=_("Invalid Medical Insurance Declaration"),
        )


    # -----------------------------------------------------
    # Tertiary Education
    # -----------------------------------------------------

    tertiary_rows = [
        row
        for row in declarations
        if row.exemption_category == TERTIARY_CATEGORY
    ]

    if len(tertiary_rows) > dependent_count:
        frappe.throw(
            _(
                "The selected dependent tier allows a maximum of {0} "
                "tertiary education deduction(s), but {1} were entered."
            ).format(
                dependent_count,
                len(tertiary_rows),
            ),
            title=_("Invalid Tertiary Education Declaration"),
        )


    # -----------------------------------------------------
    # Private School Fees
    # -----------------------------------------------------

    private_school_rows = [
        row
        for row in declarations
        if row.exemption_category == PRIVATE_SCHOOL_CATEGORY
    ]

    allowed_private_school = set(
        PRIVATE_SCHOOL_CHILDREN[:dependent_count]
    )

    invalid_private_school = [
        row.exemption_sub_category
        for row in private_school_rows
        if row.exemption_sub_category not in allowed_private_school
    ]

    if invalid_private_school:
        frappe.throw(
            _(
                "The following private school fee declaration is not "
                "allowed for the selected dependent tier: {0}"
            ).format(", ".join(invalid_private_school)),
            title=_("Invalid Private School Fee Declaration"),
        )
