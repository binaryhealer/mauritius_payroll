app_name = "mauritius_payroll"
app_title = "Mauritius Payroll"
app_publisher = "GoTech"
app_description = "Mauritius Payroll"
app_email = "julie@gotechmu.com"
app_license = "unlicense"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "mauritius_payroll",
# 		"logo": "/assets/mauritius_payroll/logo.png",
# 		"title": "Mauritius Payroll",
# 		"route": "/mauritius_payroll",
# 		"has_permission": "mauritius_payroll.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mauritius_payroll/css/mauritius_payroll.css"
# app_include_js = "/assets/mauritius_payroll/js/mauritius_payroll.js"

# include js, css files in header of web template
# web_include_css = "/assets/mauritius_payroll/css/mauritius_payroll.css"
# web_include_js = "/assets/mauritius_payroll/js/mauritius_payroll.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mauritius_payroll/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mauritius_payroll/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "mauritius_payroll.utils.jinja_methods",
# 	"filters": "mauritius_payroll.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mauritius_payroll.install.before_install"
# after_install = "mauritius_payroll.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mauritius_payroll.uninstall.before_uninstall"
# after_uninstall = "mauritius_payroll.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mauritius_payroll.utils.before_app_install"
# after_app_install = "mauritius_payroll.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mauritius_payroll.utils.before_app_uninstall"
# after_app_uninstall = "mauritius_payroll.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "mauritius_payroll.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mauritius_payroll.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["mauritius_payroll.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"mauritius_payroll.tasks.all"
# 	],
# 	"daily": [
# 		"mauritius_payroll.tasks.daily"
# 	],
# 	"hourly": [
# 		"mauritius_payroll.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mauritius_payroll.tasks.weekly"
# 	],
# 	"monthly": [
# 		"mauritius_payroll.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "mauritius_payroll.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "mauritius_payroll.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mauritius_payroll.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mauritius_payroll.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mauritius_payroll.utils.before_request"]
# after_request = ["mauritius_payroll.utils.after_request"]

# Job Events
# ----------
# before_job = ["mauritius_payroll.utils.before_job"]
# after_job = ["mauritius_payroll.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"mauritius_payroll.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

regional_overrides = {
    "Mauritius": {
        "hrms.payroll.doctype.salary_slip.salary_slip.apply_regional_deductions":
            "mauritius_payroll.payroll.salary_slip.apply_regional_deductions"
    }
}


doc_events = {
    "Salary Slip": {
        "validate": (
            "mauritius_payroll.payroll.salary_slip."
            "update_mauritius_income_tax_breakup"
        )
    },
    "Employee Tax Exemption Declaration": {
        "validate": (
            "mauritius_payroll.payroll.edf."
            "validate_edf_declaration"
        )
    }
}


fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Additional Salary-custom_mauritius_eoy_generated",
                    "Additional Salary-custom_mauritius_eoy_year",
                    "Employee-custom_mauritius_prgf_exemption",
                    "Employee Tax Exemption Declaration-custom_mauritius_edf_effective_from",
                    "Salary Component-custom_mauritius_csg_treatment",
                    "Salary Component-custom_mauritius_nsf_base",
                    "Salary Component-custom_mauritius_hrdc_levy_base",
                    "Salary Component-custom_mauritius_prgf_base",
                    "Salary Component-custom_mauritius_eoy_bonus_qualifying_earning",
                ],
            ]
        ],
    }
]



after_sync = "mauritius_payroll.setup.ensure_statutory_salary_components"
after_migrate = "mauritius_payroll.setup.ensure_statutory_salary_components"


# Desktop / Apps Screen
add_to_apps_screen = [
    {
        "name": "mauritius_payroll",
        "title": "Mauritius Payroll",
        "route": "/desk/mauritius-eoy-processing",
        "sequence_id": 30,
    }
]
