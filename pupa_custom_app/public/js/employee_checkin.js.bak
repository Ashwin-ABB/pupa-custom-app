frappe.ui.form.on("Employee Checkin", {
	onload(frm) {
		// Pre-fill the logged-in user's own Employee record
		if (frm.is_new() && !frm.doc.employee) {
			frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name").then((r) => {
				if (r.message && r.message.name) {
					frm.set_value("employee", r.message.name);
				}
			});
		}
	},

	refresh(frm) {
		// Photo can only be set through the camera button (no gallery upload)
		frm.set_df_property("checkin_photo", "read_only", 1);
		frm.set_df_property("latitude", "read_only", 1);
		frm.set_df_property("longitude", "read_only", 1);
	},

	take_selfie(frm) {
		open_selfie_dialog(frm);
	},
});

function open_selfie_dialog(frm) {
	if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
		frappe.msgprint(
			__("The camera needs a secure (HTTPS) connection and a browser that supports it.")
		);
		return;
	}

	let stream = null;
	const stop_camera = () => {
		if (stream) {
			stream.getTracks().forEach((t) => t.stop());
			stream = null;
		}
	};

	const d = new frappe.ui.Dialog({
		title: __("Take Selfie"),
		fields: [{ fieldtype: "HTML", fieldname: "cam" }],
		primary_action_label: __("Capture"),
		primary_action() {
			const video = d.$wrapper.find("video")[0];
			if (!video || !video.videoWidth) {
				return;
			}
			const canvas = document.createElement("canvas");
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			canvas.getContext("2d").drawImage(video, 0, 0);
			const blob_promise = new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.9));
			Promise.all([blob_promise, get_position()])
				.then(([blob, pos]) => upload_photo(blob, pos))
				.catch(() =>
					frappe.msgprint(
						__("Location access is required. Please allow location and try again.")
					)
				);
		},
	});

	const upload_photo = (blob, pos) => {
		const fd = new FormData();
		fd.append("file", blob, "checkin_" + Date.now() + ".jpg");
		fd.append("is_private", 1);
		fetch("/api/method/upload_file", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token, Accept: "application/json" },
			body: fd,
		})
			.then((r) => r.json())
			.then((r) => {
				if (r.message && r.message.file_url) {
					frm.set_value({
						checkin_photo: r.message.file_url,
						latitude: pos.coords.latitude,
						longitude: pos.coords.longitude,
					});
					d.hide();
					frappe.show_alert({ message: __("Photo captured"), indicator: "green" });
				} else {
					throw new Error("upload failed");
				}
			})
			.catch(() => frappe.msgprint(__("Photo upload failed. Please try again.")));
	};

	d.onhide = stop_camera;
	d.fields_dict.cam.$wrapper.html(
		'<video autoplay playsinline muted style="width:100%;border-radius:8px;transform:scaleX(-1);background:#000"></video>'
	);
	d.show();

	navigator.mediaDevices
		.getUserMedia({ video: { facingMode: "user" }, audio: false })
		.then((s) => {
			stream = s;
			d.$wrapper.find("video")[0].srcObject = s;
		})
		.catch(() => {
			frappe.msgprint(__("Could not open the camera. Please allow camera access and try again."));
			d.hide();
		});
}

function get_position() {
	return new Promise((resolve, reject) => {
		if (!navigator.geolocation) {
			reject();
			return;
		}
		navigator.geolocation.getCurrentPosition(resolve, reject, {
			enableHighAccuracy: true,
			timeout: 15000,
			maximumAge: 0,
		});
	});
}
