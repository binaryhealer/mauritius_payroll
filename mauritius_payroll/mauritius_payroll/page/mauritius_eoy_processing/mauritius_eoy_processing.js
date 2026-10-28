frappe.pages["mauritius-eoy-processing"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Mauritius EOY Processing"),
		single_column: true,
	});

	const current_year = new Date().getFullYear();

	page.company_field = page.add_field({
		fieldname: "company",
		label: __("Company"),
		fieldtype: "Link",
		options: "Company",
		reqd: 1,
		default: frappe.defaults.get_default("company"),
	});

	page.year_field = page.add_field({
		fieldname: "year",
		label: __("Year"),
		fieldtype: "Int",
		reqd: 1,
		default: current_year,
		change: function () {
			const year = page.year_field.get_value();

			if (year) {
				page.payroll_date_field.set_value(`${year}-12-31`);
			}
		},
	});

	page.payroll_date_field = page.add_field({
		fieldname: "payroll_date",
		label: __("Payroll Date"),
		fieldtype: "Date",
		reqd: 1,
		default: `${current_year}-12-31`,
	});

	const $content = $(`
		<div class="mauritius-eoy-processing">
			<div class="frappe-card p-4 mb-4">
				<h4>${__("Mauritius End of Year Bonus")}</h4>
				<p class="text-muted mb-0">
					${__(
						"Review employee EOY bonus eligibility before generating any payroll records."
					)}
				</p>
			</div>

			<div class="eoy-preview-results"></div>
			<div class="eoy-submission-results mt-4"></div>
		</div>
	`).appendTo(page.body);

	const $results = $content.find(".eoy-preview-results");
	const $submission_results = $content.find(".eoy-submission-results");

	function render_results(rows) {
		$results.empty();

		if (!rows || !rows.length) {
			$results.append(
				$("<div>")
					.addClass("frappe-card p-4 text-muted")
					.text(__("No employees found for EOY processing."))
			);
			return;
		}

		const $card = $("<div>").addClass("frappe-card");
		const $table = $("<table>").addClass(
			"table table-bordered table-hover mb-0"
		);

		const $thead = $("<thead>").append(`
			<tr>
				<th>${__("Employee")}</th>
				<th>${__("Employee Name")}</th>
				<th>${__("Regime")}</th>
				<th>${__("Qualifying Earnings")}</th>
				<th>${__("Entitlement")}</th>
				<th>${__("Already Paid")}</th>
				<th>${__("Pending")}</th>
				<th>${__("Balance Due")}</th>
				<th>${__("Available to Generate")}</th>
				<th>${__("Processing Status")}</th>
				<th>${__("Bulk Status")}</th>
				<th>${__("Missing Payroll Months")}</th>
			</tr>
		`);

		const $tbody = $("<tbody>");

		rows.forEach((row) => {
			const $tr = $("<tr>");

			const currency = frappe.defaults.get_default("currency");

			const format_amount = (value) =>
				value == null ? "-" : format_currency(value, currency);

			$("<td>").text(row.employee || "").appendTo($tr);
			$("<td>").text(row.employee_name || "").appendTo($tr);
			$("<td>").text(row.regime || "-").appendTo($tr);
			$("<td>").text(format_amount(row.qualifying_earnings)).appendTo($tr);
			$("<td>").text(format_amount(row.entitlement)).appendTo($tr);
			$("<td>").text(format_amount(row.already_paid)).appendTo($tr);
			$("<td>")
				.text(format_amount(row.pending_additional_salary))
				.appendTo($tr);
			$("<td>").text(format_amount(row.balance_due)).appendTo($tr);
			$("<td>")
				.text(format_amount(row.available_to_generate))
				.appendTo($tr);
			$("<td>").text(row.processing_status || "").appendTo($tr);
			$("<td>").text(row.bulk_status || "").appendTo($tr);
			$("<td>")
				.text(
					(row.missing_payroll_months || []).join(", ") || "-"
				)
				.appendTo($tr);

			$tbody.append($tr);
		});

		$table.append($thead);
		$table.append($tbody);
		$card.append($table);
		$results.append($card);
	}


	function render_submission_results(rows) {
		$submission_results.empty();

		const $title = $("<div>").addClass("mb-2");
		$("<h4>")
			.text(__("EOY Drafts Awaiting Submission"))
			.appendTo($title);

		$submission_results.append($title);

		if (!rows || !rows.length) {
			$submission_results.append(
				$("<div>")
					.addClass("frappe-card p-4 text-muted")
					.text(__("No generated EOY drafts are awaiting submission."))
			);
			return;
		}

		const currency = frappe.defaults.get_default("currency");
		const format_amount = (value) =>
			value == null ? "-" : format_currency(value, currency);

		const $card = $("<div>").addClass("frappe-card");
		const $table = $("<table>").addClass(
			"table table-bordered table-hover mb-0"
		);

		const $thead = $("<thead>").append(`
			<tr>
				<th>${__("Additional Salary")}</th>
				<th>${__("Employee")}</th>
				<th>${__("Payroll Date")}</th>
				<th>${__("Amount")}</th>
				<th>${__("Submission Status")}</th>
				<th>${__("Processing Status")}</th>
				<th>${__("Balance Due")}</th>
				<th>${__("Pending")}</th>
				<th>${__("Error")}</th>
			</tr>
		`);

		const $tbody = $("<tbody>");

		rows.forEach((row) => {
			const $tr = $("<tr>");

			$("<td>").text(row.additional_salary || "").appendTo($tr);
			$("<td>").text(row.employee || "").appendTo($tr);
			$("<td>").text(row.payroll_date || "-").appendTo($tr);
			$("<td>").text(format_amount(row.amount)).appendTo($tr);
			$("<td>").text(row.submission_status || "").appendTo($tr);
			$("<td>").text(row.processing_status || "-").appendTo($tr);
			$("<td>").text(format_amount(row.balance_due)).appendTo($tr);
			$("<td>")
				.text(format_amount(row.pending_additional_salary))
				.appendTo($tr);
			$("<td>").text(row.error || "-").appendTo($tr);

			$tbody.append($tr);
		});

		$table.append($thead);
		$table.append($tbody);
		$card.append($table);
		$submission_results.append($card);
	}

	let submission_review = {
		company: null,
		year: null,
		ready_count: 0,
	};

	const $submit_eoy_button = page.add_inner_button(
		__("Submit EOY Drafts"),
		async function () {
			const company = page.company_field.get_value();
			const year = page.year_field.get_value();

			if (
				submission_review.ready_count <= 0 ||
				submission_review.company !== company ||
				String(submission_review.year) !== String(year)
			) {
				frappe.msgprint(
					__(
						"Please run Review Drafts for Submission again before submitting."
					)
				);
				return;
			}

			frappe.confirm(
				__(
					"Submit {0} EOY Additional Salary draft(s)? Submitted records cannot be edited as Drafts.",
					[submission_review.ready_count]
				),
				async function () {
					const response = await frappe.call({
						method: "mauritius_payroll.api.submit_eoy_bonus_drafts",
						args: {
							company: company,
							year: year,
						},
						freeze: true,
						freeze_message: __("Submitting EOY drafts..."),
					});

					const results = response.message || [];
					const submitted = results.filter(
						(row) => row.bulk_submission_status === "Submitted"
					).length;
					const skipped = results.filter(
						(row) => row.bulk_submission_status === "Skipped"
					).length;
					const validation_errors = results.filter(
						(row) =>
							row.bulk_submission_status === "Validation Error"
					).length;

					submission_review = {
						company: null,
						year: null,
						ready_count: 0,
					};
					$submit_eoy_button.prop("disabled", true);

					const review = await frappe.call({
						method: "mauritius_payroll.api.preview_eoy_bonus_submission",
						args: {
							company: company,
							year: year,
						},
						freeze: true,
						freeze_message: __("Refreshing submission review..."),
					});

					render_submission_results(review.message || []);

					frappe.msgprint({
						title: __("EOY Submission Complete"),
						message: __(
							"Submitted: {0}<br>Skipped: {1}<br>Validation Errors: {2}",
							[submitted, skipped, validation_errors]
						),
						indicator:
							validation_errors > 0 ? "orange" : "green",
					});
				}
			);
		}
	);

	$submit_eoy_button.prop("disabled", true);

	function invalidate_submission_review() {
		submission_review = {
			company: null,
			year: null,
			ready_count: 0,
		};

		$submit_eoy_button.prop("disabled", true);
		$submission_results.empty();
	}

	const original_company_change = page.company_field.df.change;
	page.company_field.df.change = function () {
		if (original_company_change) {
			original_company_change();
		}

		invalidate_submission_review();
	};

	const original_year_change = page.year_field.df.change;
	page.year_field.df.change = function () {
		if (original_year_change) {
			original_year_change();
		}

		invalidate_submission_review();
	};

	page.add_inner_button(
		__("Review Drafts for Submission"),
		async function () {
			const company = page.company_field.get_value();
			const year = page.year_field.get_value();

			if (!company) {
				frappe.msgprint(__("Please select a Company."));
				return;
			}

			if (!year) {
				frappe.msgprint(__("Please enter the EOY Year."));
				return;
			}

			const response = await frappe.call({
				method: "mauritius_payroll.api.preview_eoy_bonus_submission",
				args: {
					company: company,
					year: year,
				},
				freeze: true,
				freeze_message: __("Reviewing EOY drafts..."),
			});

			const rows = response.message || [];

			render_submission_results(rows);

			const ready_count = rows.filter(
				(row) => row.submission_status === "Ready to Submit"
			).length;

			submission_review = {
				company: company,
				year: year,
				ready_count: ready_count,
			};

			$submit_eoy_button.prop("disabled", ready_count === 0);
		}
	);

	page.set_primary_action(__("Preview EOY"), async function () {
		const company = page.company_field.get_value();
		const year = page.year_field.get_value();
		const payroll_date = page.payroll_date_field.get_value();

		if (!company) {
			frappe.msgprint(__("Please select a Company."));
			return;
		}

		if (!year) {
			frappe.msgprint(__("Please enter the EOY Year."));
			return;
		}

		if (!payroll_date) {
			frappe.msgprint(__("Please select a Payroll Date."));
			return;
		}

		const response = await frappe.call({
			method: "mauritius_payroll.api.preview_eoy_bonus_generation",
			args: {
				company: company,
				year: year,
				payroll_date: payroll_date,
			},
			freeze: true,
			freeze_message: __("Preparing EOY preview..."),
		});

		render_results(response.message || []);
	});

	page.set_secondary_action(__("Generate EOY Drafts"), function () {
		const company = page.company_field.get_value();
		const year = page.year_field.get_value();
		const payroll_date = page.payroll_date_field.get_value();

		if (!company) {
			frappe.msgprint(__("Please select a Company."));
			return;
		}

		if (!year) {
			frappe.msgprint(__("Please enter the EOY Year."));
			return;
		}

		if (!payroll_date) {
			frappe.msgprint(__("Please select a Payroll Date."));
			return;
		}

		frappe.confirm(
			__(
				"Generate draft Additional Salary records for employees currently eligible for EOY bonus?"
			),
			async function () {
				await frappe.call({
					method: "mauritius_payroll.api.generate_eoy_bonus_drafts",
					args: {
						company: company,
						year: year,
						payroll_date: payroll_date,
					},
					freeze: true,
					freeze_message: __("Generating EOY drafts..."),
				});

				const preview = await frappe.call({
					method: "mauritius_payroll.api.preview_eoy_bonus_generation",
					args: {
						company: company,
						year: year,
						payroll_date: payroll_date,
					},
					freeze: true,
					freeze_message: __("Refreshing EOY preview..."),
				});

				render_results(preview.message || []);

				frappe.show_alert({
					message: __("EOY draft generation completed. Preview refreshed."),
					indicator: "green",
				});
			}
		);
	}, "add");

};
