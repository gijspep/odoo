import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";

const POLL_MS = 1500;

class InstructView extends Component {
    static template = "email_parser.InstructView";
    static props = {};

    setup() {
        this.state = useState({ body: "", files: [], jobs: [] });
        this.fileInputRef = useRef("fileInput");
        this._nextJobId = 0;
        this._nextFileId = 0;
    }

    addFiles(fileList) {
        for (const f of fileList) {
            this.state.files.push({ id: this._nextFileId++, file: f });
        }
    }

    removeFile(id) {
        const idx = this.state.files.findIndex((f) => f.id === id);
        if (idx !== -1) this.state.files.splice(idx, 1);
    }

    onDropZoneClick() {
        this.fileInputRef.el.click();
    }

    onFileChange(ev) {
        this.addFiles(ev.target.files);
        ev.target.value = "";
    }

    onDragOver(ev) {
        ev.preventDefault();
        ev.currentTarget.classList.add("ep-drag-over");
    }

    onDragLeave(ev) {
        ev.currentTarget.classList.remove("ep-drag-over");
    }

    onDrop(ev) {
        ev.preventDefault();
        ev.currentTarget.classList.remove("ep-drag-over");
        this.addFiles(ev.dataTransfer.files);
    }

    async onSubmit() {
        if (!this.state.body.trim() && this.state.files.length === 0) return;

        const id = this._nextJobId++;
        this.state.jobs.unshift({
            id,
            status: "Uploading",
            badgeCls: "bg-secondary",
            jobRef: null,
            progress: "Sending…",
            resultLink: null,
        });

        const job = () => this.state.jobs.find((j) => j.id === id);

        try {
            const form = new FormData();
            form.append("body_content", this.state.body.trim());
            this.state.files.forEach((f) => form.append("attachments", f.file));

            const resp = await fetch("/email_parser/instruct", { method: "POST", body: form });
            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            job().jobRef = data.id;
            job().status = "Pending";
            job().badgeCls = "bg-info text-dark";
            job().progress = "Waiting for result…";

            while (true) {
                await new Promise((r) => setTimeout(r, POLL_MS));
                const pollResp = await fetch(`/email_parser/poll/${data.id}`);
                const result = await pollResp.json();
                if (result.error) throw new Error(result.error);
                if (result.status !== "PENDING") {
                    const ok = result.status_code >= 200 && result.status_code < 300;
                    job().status = result.status;
                    job().badgeCls = ok ? "bg-success" : "bg-danger";
                    job().progress = null;
                    job().resultLink = result.extraction_id
                        ? `/odoo/parser-extractions/${result.extraction_id}`
                        : "/odoo/parser-extractions";
                    return;
                }
            }
        } catch (err) {
            const j = job();
            if (j) {
                j.status = "Error";
                j.badgeCls = "bg-danger";
                j.progress = err.message;
            }
        }
    }
}

registry.category("actions").add("email_parser.instruct_view", InstructView);
