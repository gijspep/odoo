import { Component, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";

const POLL_MS = 1500;

class UploadView extends Component {
    static template = "email_parser.UploadView";
    static props = {};

    setup() {
        this.state = useState({ jobs: [] });
        this.fileInputRef = useRef("fileInput");
        this._nextId = 0;
    }

    async processFile(file) {
        const id = this._nextId++;
        this.state.jobs.unshift({
            id,
            filename: file.name,
            status: "Uploading",
            badgeCls: "bg-secondary",
            jobRef: null,
            progress: "Sending file…",
            resultLink: null,
        });

        const job = () => this.state.jobs.find((j) => j.id === id);

        try {
            const form = new FormData();
            form.append("msg_file", file);
            const resp = await fetch("/email_parser/submit", { method: "POST", body: form });
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

    onZoneClick() {
        this.fileInputRef.el.click();
    }

    onFileChange(ev) {
        [...ev.target.files].forEach((f) => this.processFile(f));
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
        const files = [...ev.dataTransfer.files].filter((f) =>
            f.name.toLowerCase().endsWith(".msg")
        );
        files.forEach((f) => this.processFile(f));
    }
}

registry.category("actions").add("email_parser.upload_view", UploadView);
