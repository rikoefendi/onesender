// TODO: revisit and properly implement this client script
frappe.pages["print"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
	});
	let print_view = new frappe.ui.form.PrintView(wrapper);

	$(wrapper).bind("show", () => {
		const route = frappe.get_route();
		const doctype = route[1];
		const docname = route.slice(2).join("/");
		if (!frappe.route_options || !frappe.route_options.frm) {
			frappe.model.with_doc(doctype, docname, () => {
				let frm = { doctype: doctype, docname: docname };
				frm.doc = frappe.get_doc(doctype, docname);
				frappe.model.with_doctype(doctype, () => {
					frm.meta = frappe.get_meta(route[1]);
					print_view.show(frm);
				});
			});
		} else {
			print_view.frm = frappe.route_options.frm.doctype
				? frappe.route_options.frm
				: frappe.route_options.frm.frm;
			frappe.route_options.frm = null;
			print_view.show(print_view.frm);
		}
	});
};
frappe.ui.form.PrintView = class PrintView extends frappe.ui.form.PrintView {
	constructor(wrapper) {
		super(wrapper);
	}
	make() {
		super.make();
		this.print_wrapper = this.page.main.append(
			`<div class="print-designer-wrapper">
				<div id="preview-container" class="preview-container"
					style="background-color: white; position: relative;">
					${frappe.render_template("print_skeleton_loading")}
				</div>
			</div>`
		);
		//shorcut print
		frappe.ui.keys.add_shortcut({
			shortcut: "ctrl+p",
			description: __("Print document"), // Description shown in help
			action: () => { 
				this.printit()
			 } // Action to perform
		});
	}

	isTekma(){
		let print_format = this.get_print_format();
        return print_format.pdf_generator == "tekma"
	}
	createPdfEl(url, wrapperContainer) {
		let pdfEl = document.getElementById("pd-pdf-viewer");
		if (!pdfEl) {
			pdfEl = document.createElement("object");
			pdfEl.id = "pd-pdf-viewer";
			pdfEl.type = "application/pdf";
			wrapperContainer.appendChild(pdfEl);
		}
		pdfEl.style.height = "0px";

		pdfEl.data = url;
		pdfEl.style.width = "100%";

		return pdfEl;
	}
	preview() {
		super.preview();
		this.wrapper.find('.print-preview').css({
			maxWidth: "100%",
			maxHeight: "100%",
			width: "auto"
		})
	}
	get_print_html(callback) {
		let print_format = this.get_print_format();
		if (print_format.raw_printing) {
			callback({
				html: this.get_no_preview_html(),
			});
			return;
		}
		if (this._req) {
			this._req.abort();
		}
		let method = "frappe.www.printview.get_html_and_style"
		if(this.isTekma()){
			method = "onesender.www.printview.get_html_and_style"
		}
		this._req = frappe.call({
			method,
			args: {
				doc: this.frm.doc,
				print_format: this.selected_format(),
				no_letterhead: !this.with_letterhead() ? 1 : 0,
				letterhead: this.get_letterhead(),
				settings: this.additional_settings,
				_lang: this.lang_code,
			},
			callback: function (r) {
				if (!r.exc) {
					callback(r.message);
				}
			},
		});
	}
};