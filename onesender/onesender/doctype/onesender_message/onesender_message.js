const save_send_message = async (frm) => {
			if(frm.is_new()) return frm.save()
			if(frm.is_dirty()) await frm.save()
			frappe.call({
				method: "onesender.onesender.doctype.onesender_message.onesender_message.resend_message",
				args: {
					docname: frm.doc.name
				},
				freeze: true,
				callback(r) {
					if (r.message) {
						// frappe.msgprint(r.message);
						frm.reload_doc();
					}
				}
			});
	}

frappe.ui.form.on("Onesender Message", {
	setup(frm){
		frappe.ui.keys.add_shortcut({
            shortcut: 'f2',
            action: () => {
                save_send_message(frm)
            },
            description: 'Save and Re/Send Message via shortcut',
            action_label: 'Save and Re/Send Message'
        });
		frm.disable_save();
	},
	onload(frm){

	},
	before_save(frm) {
		if (frm.doc.__unsaved && frm.doc.attach) {
			return false; // Prevent auto-save
		}
	},
	attach_with_doctype(frm) {
		if (!frm.doc.attach_with_doctype) {
			delete frm.doc.attach_docname;
			delete frm.doc.attach_doctype;
		}
	},
	attach_doctype(frm) {
		// Reset target_docname dan set Link options sesuai target_doctype
		frm.set_value("attach_docname", "");

		if (frm.doc.attach_doctype) {
			frm.set_df_property("attach_docname", "options", frm.doc.attach_doctype);
			frm.refresh_field("attach_docname");
		}
	},
	refresh(frm) {
		frm.add_custom_button(__(`Save & ${frm.is_new()?'Send': 'Resend'} (F2)`), async () => {
			await save_send_message(frm)
		});
	}
});



// frappe.ui.form.on('Your Doctype Name', {
//     refresh: function(frm) {
//         if (frm.doc.status === 'Draft') {
//             frm.add_custom_button(__('Proses Sekarang'), () => {
//                 // contoh panggil method Python
//                 frappe.call({
//                     method: "your_app.api.nama_method",
//                     args: {
//                         docname: frm.doc.name
//                     },
//                     callback: function(r) {
//                         if (r.message) {
//                             frappe.msgprint('Berhasil diproses!');
//                             frm.reload_doc();
//                         }
//                     }
//                 });
//             }, 'Actions');
//         }
//     }
// });
