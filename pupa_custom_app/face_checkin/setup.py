import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def create_fields():
	"""Run once: bench --site dev.local execute pupa_custom_app.face_checkin.setup.create_fields"""
	meta = frappe.get_meta("Employee Checkin")
	geo = []
	for fn, label in (("latitude", "Latitude"), ("longitude", "Longitude")):
		if not meta.has_field(fn):
			geo.append(
				{
					"fieldname": fn,
					"label": label,
					"fieldtype": "Float",
					"precision": "9",
					"read_only": 1,
					"insert_after": "face_match_score",
				}
			)

	create_custom_fields(
		{
			"Employee Checkin": [
				{
					"fieldname": "face_section",
					"label": "Face Verification",
					"fieldtype": "Section Break",
					"insert_after": "log_type",
				},
				{
					"fieldname": "take_selfie",
					"label": "Take Selfie",
					"fieldtype": "Button",
					"insert_after": "face_section",
				},
				{
					"fieldname": "fc_photo",
					"label": "Check-in Photo",
					"fieldtype": "Attach Image",
					"insert_after": "take_selfie",
				},
				{
					"fieldname": "face_match_status",
					"label": "Face Match Status",
					"fieldtype": "Select",
					"options": "\nNot Checked\nVerified\nMismatch\nNo Face Detected\nNo Master Photo",
					"read_only": 1,
					"no_copy": 1,
					"insert_after": "fc_photo",
				},
				{
					"fieldname": "face_match_score",
					"label": "Face Match Score",
					"fieldtype": "Float",
					"precision": "3",
					"read_only": 1,
					"no_copy": 1,
					"insert_after": "face_match_status",
				},
			]
			+ geo
		},
		update=True,
	)

	# Mark selfie + location mandatory on the form (and on the server).
	# Biometric device check-ins (they carry a Device ID) are exempt.
	for fn in ("fc_photo", "latitude", "longitude"):
		make_property_setter(
			"Employee Checkin", fn, "mandatory_depends_on", "eval:!doc.device_id", "Code"
		)
	frappe.clear_cache(doctype="Employee Checkin")
