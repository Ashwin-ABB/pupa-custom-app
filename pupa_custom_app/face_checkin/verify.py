"""Face verification for Employee Checkin (OpenCV YuNet detector + SFace recogniser).

Site config (optional):
  face_checkin_mode       "block" (default, reject mismatches) or "flag" (save, mark Mismatch)
  face_checkin_threshold  cosine similarity, default 0.363 (OpenCV's recommended value)
"""
import json
import os

import frappe
from frappe import _

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DETECTOR_MODEL = "face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = "face_recognition_sface_2021dec.onnx"
PRIVILEGED_ROLES = {"System Manager", "HR Manager"}

_models = {}


def _get_models():
	if not _models:
		import cv2

		det_path = os.path.join(MODEL_DIR, DETECTOR_MODEL)
		rec_path = os.path.join(MODEL_DIR, RECOGNIZER_MODEL)
		for p in (det_path, rec_path):
			if not os.path.exists(p):
				frappe.throw(_("Face model file missing: {0}").format(os.path.basename(p)))
		_models["det"] = cv2.FaceDetectorYN.create(det_path, "", (320, 320), 0.8)
		_models["rec"] = cv2.FaceRecognizerSF.create(rec_path, "")
	return _models["det"], _models["rec"]


def _read_image(file_url):
	import cv2

	file_doc = frappe.get_doc("File", {"file_url": file_url})
	img = cv2.imread(file_doc.get_full_path())
	if img is None:
		return None
	h, w = img.shape[:2]
	scale = 1000.0 / max(h, w)
	if scale < 1:
		img = cv2.resize(img, (int(w * scale), int(h * scale)))
	return img


def _embedding(img):
	det, rec = _get_models()
	h, w = img.shape[:2]
	det.setInputSize((w, h))
	_, faces = det.detect(img)
	if faces is None or len(faces) == 0:
		return None
	face = max(faces, key=lambda f: f[2] * f[3])  # largest face
	return rec.feature(rec.alignCrop(img, face))


def compare(photo_url, master_url):
	"""Returns (status, score)."""
	import cv2

	_, rec = _get_models()
	a, b = _read_image(photo_url), _read_image(master_url)
	if a is None or b is None:
		return "No Face Detected", None
	ea, eb = _embedding(a), _embedding(b)
	if ea is None or eb is None:
		return "No Face Detected", None
	score = float(rec.match(ea, eb, cv2.FaceRecognizerSF_FR_COSINE))
	threshold = float(frappe.conf.get("face_checkin_threshold", 0.363))
	return ("Verified" if score >= threshold else "Mismatch"), score


def validate_checkin_face(doc, method=None):
	if doc.get("device_id"):  # biometric devices push check-ins without photos
		return
	if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_import:
		return

	# 1. Only the logged-in employee can check in for themselves
	if not (PRIVILEGED_ROLES & set(frappe.get_roles())):
		own = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if own != doc.employee:
			frappe.throw(_("You can only check in for your own employee record."))

	# 2. Photo is required
	if not doc.fc_photo:
		frappe.throw(_("Please upload a check-in photo."))

	# Location is required (captured automatically by the Take Selfie button)
	if not doc.get("latitude") or not doc.get("longitude"):
		frappe.throw(_("Location is required. Please allow location access and retake the selfie."))

	# Fill the map pin so HR can see the check-in location on the Geolocation field
	doc.geolocation = json.dumps(
		{
			"type": "FeatureCollection",
			"features": [
				{
					"type": "Feature",
					"properties": {},
					"geometry": {
						"type": "Point",
						"coordinates": [float(doc.longitude), float(doc.latitude)],
					},
				}
			],
		}
	)

	if not doc.is_new() and not doc.has_value_changed("fc_photo"):
		return

	# 3. Compare with the Employee master photo
	master = frappe.db.get_value("Employee", doc.employee, "image")
	if not master:
		doc.fc_match_status = "No Master Photo"
		frappe.throw(_("No photo found in the Employee master for {0}.").format(doc.employee))

	status, score = compare(doc.fc_photo, master)
	doc.fc_match_status = status
	doc.fc_match_score = score

	if status == "Verified":
		doc.skip_auto_attendance = 0
		return

	# Unverified check-ins (flag mode) stay out of auto attendance until HR approves them
	doc.skip_auto_attendance = 1
	if frappe.conf.get("face_checkin_mode", "block") == "block":
		msg = (
			_("No face detected in the photo. Please retake it facing the camera.")
			if status == "No Face Detected"
			else _("Face does not match the employee record.")
		)
		frappe.throw(msg)
