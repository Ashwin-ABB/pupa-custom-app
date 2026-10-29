import base64

import frappe
from frappe import _
from frappe.utils import nowdate, now_datetime

MAX_PHOTO_BYTES = 3 * 1024 * 1024


def _employee_of_session_user():
	emp = frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user, "status": "Active"}, "name"
	)
	if not emp:
		frappe.throw(_("No active Employee record is linked to your user."))
	return emp


@frappe.whitelist()
def get_today_logs():
	employee = _employee_of_session_user()
	return frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [nowdate() + " 00:00:00", nowdate() + " 23:59:59"]],
		},
		fields=["name", "log_type", "time", "face_match_status"],
		order_by="time asc",
	)


@frappe.whitelist(methods=["POST"])
def submit_checkin(log_type, photo, latitude, longitude):
	if log_type not in ("IN", "OUT"):
		frappe.throw(_("Invalid log type."))
	employee = _employee_of_session_user()

	try:
		content = base64.b64decode(photo.split(",", 1)[-1])
		lat, lng = float(latitude), float(longitude)
	except Exception:
		frappe.throw(_("Invalid photo or location data."))
	if len(content) > MAX_PHOTO_BYTES or not content.startswith(b"\xff\xd8"):
		frappe.throw(_("Photo must be a JPEG under 3 MB."))

	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": "checkin_{}_{}.jpg".format(employee, now_datetime().strftime("%Y%m%d%H%M%S")),
			"content": content,
			"is_private": 1,
		}
	).insert(ignore_permissions=True)

	try:
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": log_type,
				"time": now_datetime(),
				"fc_photo": file_doc.file_url,
				"latitude": lat,
				"longitude": lng,
			}
		).insert()
	except Exception:
		# don't leave an orphan photo behind when verification fails
		frappe.delete_doc("File", file_doc.name, ignore_permissions=True, force=True)
		raise

	frappe.db.set_value(
		"File",
		file_doc.name,
		{
			"attached_to_doctype": "Employee Checkin",
			"attached_to_name": checkin.name,
			"attached_to_field": "fc_photo",
		},
	)
	return {
		"name": checkin.name,
		"log_type": checkin.log_type,
		"time": str(checkin.time),
		"face_match_status": checkin.get("face_match_status"),
		"face_match_score": checkin.get("face_match_score"),
	}
