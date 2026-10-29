import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/checkin"
		raise frappe.Redirect

	context.employee = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user}, ["name", "employee_name"], as_dict=True
	)
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.no_cache = 1
