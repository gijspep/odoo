import base64
import json
import logging

import requests as http_requests
from cryptography.exceptions import InvalidTag

from odoo import http
from odoo.http import Response, request

from odoo.addons.email_parser.crypto import (
    decrypt_key,
    decrypt_response,
    encrypt_payload,
)

_logger = logging.getLogger(__name__)

# Decrypted AES key held in memory after unlock. None until unlocked.
# Note: in a multi-worker deployment each worker must be unlocked independently.
_cached_key: bytes | None = None

COMPANY_UID = "9F6C2A48-7B1E-4D3B-AE42-1C8E7F4A0D95"
EXTERNAL_API = "http://localhost:8000"


def _load_and_decrypt(password: str) -> bytes:
    """Retrieve the stored api_key record and decrypt it with *password*.
    Raises InvalidTag on wrong password, ValueError if no key is configured."""
    record = request.env["parser.api_key"].sudo().search([], limit=1)
    if not record:
        raise ValueError("No API key configured.")
    return decrypt_key(
        bytes(record.encrypted_key),
        bytes(record.salt),
        bytes(record.nonce),
        password,
    )


class EmailParserController(http.Controller):
    # ── Portal landing ────────────────────────────────────────────────────────

    @http.route("/email_parser", type="http", auth="public")
    def portal_landing_page(self, **kwargs):
        key_set = bool(request.env["parser.api_key"].sudo().search([], limit=1))
        return request.render(
            "email_parser.standalone_portal_template",
            {
                "key_unlocked": _cached_key is not None,
                "key_set": key_set,
                "csrf_token": request.csrf_token(),
            },
        )

    # ── Unlock ────────────────────────────────────────────────────────────────

    @http.route(
        "/email_parser/unlock",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=True,
    )
    def unlock_key(self, password=None, **kwargs):
        global _cached_key
        error = None

        if not password:
            error = "Password is required."
        else:
            try:
                _cached_key = _load_and_decrypt(password)
            except (InvalidTag, Exception):
                error = "Incorrect password."

        if error:
            key_set = bool(request.env["parser.api_key"].sudo().search([], limit=1))
            return request.render(
                "email_parser.standalone_portal_template",
                {
                    "key_unlocked": False,
                    "key_set": key_set,
                    "unlock_error": error,
                    "csrf_token": request.csrf_token(),
                },
            )

        return request.redirect("/email_parser")

    # ── Job submission (proxy) ────────────────────────────────────────────────

    @http.route(
        "/email_parser/submit",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def submit_job(self, msg_file=None, **kwargs):
        if _cached_key is None:
            return Response(
                json.dumps({"error": "Server key not unlocked."}),
                status=403,
                content_type="application/json",
            )
        if not msg_file:
            return Response(
                json.dumps({"error": "No file provided."}),
                status=400,
                content_type="application/json",
            )

        try:
            file_bytes = msg_file.read()
            payload = encrypt_payload(_cached_key, file_bytes, msg_file.filename)
            resp = http_requests.post(
                f"{EXTERNAL_API}/job/{COMPANY_UID}",
                data=payload,
                headers={"Content-Type": "application/octet-stream"},
                timeout=30,
            )
            result = decrypt_response(_cached_key, resp.content)
        except Exception as exc:
            _logger.exception("submit_job failed")
            return Response(
                json.dumps({"error": str(exc)}),
                status=500,
                content_type="application/json",
            )

        return Response(json.dumps(result), content_type="application/json")

    # ── Instruct submission (proxy) ───────────────────────────────────────────

    @http.route(
        "/email_parser/instruct",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def submit_instruct(self, body_content="", **kwargs):
        if _cached_key is None:
            return Response(
                json.dumps({"error": "Server key not unlocked."}),
                status=403,
                content_type="application/json",
            )

        files_data = []
        for f in request.httprequest.files.getlist("attachments"):
            content = base64.b64encode(f.read()).decode("utf-8")
            mime = f.content_type or "application/octet-stream"
            ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
            files_data.append({
                "fileName": f.filename,
                "fileType": ext,
                "contentType": mime,
                "content": content,
            })

        try:
            json_bytes = json.dumps(
                {"bodyContent": body_content, "files": files_data}
            ).encode("utf-8")
            payload = encrypt_payload(_cached_key, json_bytes, "instruction.json")
            resp = http_requests.post(
                f"{EXTERNAL_API}/job/{COMPANY_UID}",
                data=payload,
                headers={"Content-Type": "application/octet-stream"},
                timeout=30,
            )
            result = decrypt_response(_cached_key, resp.content)
        except Exception as exc:
            _logger.exception("submit_instruct failed")
            return Response(
                json.dumps({"error": str(exc)}),
                status=500,
                content_type="application/json",
            )

        return Response(json.dumps(result), content_type="application/json")

    # ── Job polling (proxy) ───────────────────────────────────────────────────

    @http.route(
        "/email_parser/poll/<string:job_id>",
        type="http",
        auth="public",
        csrf=False,
    )
    def poll_job(self, job_id, **kwargs):
        if _cached_key is None:
            return Response(
                json.dumps({"error": "Server key not unlocked."}),
                status=403,
                content_type="application/json",
            )

        try:
            resp = http_requests.get(f"{EXTERNAL_API}/job/{job_id}", timeout=30)
            result = decrypt_response(_cached_key, resp.content)
        except Exception as exc:
            _logger.exception("poll_job failed")
            return Response(
                json.dumps({"error": str(exc)}),
                status=500,
                content_type="application/json",
            )

        if result.get("status") != "PENDING":
            try:
                extraction = self._save_extraction(job_id, result)
                result["extraction_id"] = extraction.id
                result["nomination_count"] = len(extraction.nominations)
                if result["nomination_count"] == 1:
                    result["nomination_id"] = extraction.nominations[0].id
            except Exception:
                _logger.exception("_save_extraction failed for job %s", job_id)

        return Response(json.dumps(result), content_type="application/json")

    # ── List / detail API ─────────────────────────────────────────────────────

    @http.route("/email_parser/api/extractions", type="http", auth="public", csrf=False)
    def api_list_extractions(self, **kwargs):
        extractions = (
            request.env["parser.extraction"].sudo().search([], order="id desc")
        )
        data = [
            {
                "id": e.id,
                "job_id": e.job_id or "",
                "subject": e.subject or "",
                "email_from": e.email_from or "",
                "nomination_count": len(e.nominations),
            }
            for e in extractions
        ]
        return Response(json.dumps(data), content_type="application/json")

    @http.route(
        "/email_parser/api/extraction/<int:extraction_id>",
        type="http",
        auth="public",
        csrf=False,
    )
    def api_get_extraction(self, extraction_id, **kwargs):
        extraction = request.env["parser.extraction"].sudo().browse(extraction_id)
        if not extraction.exists():
            return Response(
                json.dumps({"error": "Not found"}),
                status=404,
                content_type="application/json",
            )
        data = {
            "result": {
                "data": {
                    "from": extraction.email_from or "",
                    "subject": extraction.subject or "",
                    "nominations": [
                        self._nomination_to_dict(n) for n in extraction.nominations
                    ],
                }
            }
        }
        return Response(json.dumps(data), content_type="application/json")

    @http.route("/email_parser/api/nominations", type="http", auth="public", csrf=False)
    def api_list_nominations(self, **kwargs):
        nominations = (
            request.env["parser.nomination"].sudo().search([], order="id desc")
        )
        data = [
            {
                "id": n.id,
                "nomination_type": n.nomination_type or "",
                "arrival_date": str(n.arrival_date) if n.arrival_date else None,
                "transporter": n.transporter.name if n.transporter else "",
                "receiver": n.receiver.name if n.receiver else "",
                "sender": n.sender.name if n.sender else "",
                "references": {r.label: r.value for r in n.references},
                "subject": n.extraction_id.subject if n.extraction_id else "",
            }
            for n in nominations
        ]
        return Response(json.dumps(data), content_type="application/json")

    @http.route(
        "/email_parser/api/nomination/<int:nomination_id>",
        type="http",
        auth="public",
        csrf=False,
    )
    def api_get_nomination(self, nomination_id, **kwargs):
        nom = request.env["parser.nomination"].sudo().browse(nomination_id)
        if not nom.exists():
            return Response(
                json.dumps({"error": "Not found"}),
                status=404,
                content_type="application/json",
            )
        data = {
            "result": {
                "data": {
                    "from": nom.extraction_id.email_from if nom.extraction_id else "",
                    "subject": nom.extraction_id.subject if nom.extraction_id else "",
                    "nominations": [self._nomination_to_dict(nom)],
                }
            }
        }
        return Response(json.dumps(data), content_type="application/json")

    def _nomination_to_dict(self, nom):
        return {
            "references": {r.label: r.value for r in nom.references},
            "product_transfers": [
                {
                    "product_name": pt.product_name or "",
                    "amount": pt.amount,
                    "unit_of_measurement": pt.unit_of_measurement or "",
                    "customs_type": pt.customs_type or "",
                    "country_of_origin": pt.country_of_origin or "",
                    "source_modality": {
                        "modality_type": pt.source_modality.modality_type or "",
                        "identifier": pt.source_modality.identifier or "",
                        "ship_name": pt.source_modality.ship_name or "",
                    }
                    if pt.source_modality
                    else None,
                    "destination_modality": {
                        "modality_type": pt.destination_modality.modality_type or "",
                        "identifier": pt.destination_modality.identifier or "",
                        "ship_name": pt.destination_modality.ship_name or "",
                    }
                    if pt.destination_modality
                    else None,
                }
                for pt in nom.product_transfers
            ],
            "arrival_date": str(nom.arrival_date) if nom.arrival_date else None,
            "transporter": nom.transporter.name if nom.transporter else None,
            "receiver": nom.receiver.name if nom.receiver else None,
            "sender": nom.sender.name if nom.sender else None,
            "agent": nom.agent or None,
            "nomination_type": nom.nomination_type or "",
            "survey": {
                "sample_required": nom.sample_required,
                "inspection_before": nom.inspection_before,
                "inspection_after": nom.inspection_after,
                "certificate_of_analysis": nom.certificate_of_analysis,
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_create_company(self, name):
        if not name:
            return False
        env = request.env["parser.company"].sudo()
        company = env.search([("name", "=ilike", name)], limit=1)
        if not company:
            company = env.create({"name": name})
        return company.id

    def _create_modality(self, mod_data):
        if not mod_data:
            return False
        return (
            request.env["parser.modality"]
            .sudo()
            .create(
                {
                    "modality_type": (mod_data.get("modality_type") or "").upper(),
                    "identifier": mod_data.get("identifier") or False,
                    "ship_name": mod_data.get("ship_name") or False,
                    "ship_type": mod_data.get("ship_type") or False,
                }
            )
            .id
        )

    def _save_extraction(self, job_id, result):
        env = request.env
        # Idempotency: reuse existing record if job was already saved
        existing = (
            env["parser.extraction"].sudo().search([("job_id", "=", job_id)], limit=1)
        )
        if existing:
            return existing

        data = (result.get("result") or {}).get("data") or {}

        nominations_vals = []
        for nom_data in data.get("nominations") or []:
            pt_vals = []
            for pt_data in nom_data.get("product_transfers") or []:
                source_id = self._create_modality(pt_data.get("source_modality"))
                dest_id = self._create_modality(pt_data.get("destination_modality"))
                pt_vals.append(
                    (
                        0,
                        0,
                        {
                            "source_modality": source_id,
                            "destination_modality": dest_id,
                            "product_name": pt_data.get("product_name") or "",
                            "unit_of_measurement": (
                                pt_data.get("unit_of_measurement") or ""
                            ).upper(),
                            "amount": float(pt_data.get("amount") or 0),
                            "customs_type": (pt_data.get("customs_type") or "").upper(),
                            "country_of_origin": pt_data.get("country_of_origin")
                            or False,
                        },
                    )
                )

            ref_vals = []
            refs = nom_data.get("references") or {}
            if isinstance(refs, dict):
                for label, value in refs.items():
                    ref_vals.append((0, 0, {"label": label, "value": str(value)}))

            survey = nom_data.get("survey") or {}
            arrival_raw = nom_data.get("arrival_date") or ""
            arrival_date = (
                arrival_raw.split("T")[0]
                if "T" in arrival_raw
                else arrival_raw or False
            )

            nominations_vals.append(
                (
                    0,
                    0,
                    {
                        "arrival_date": arrival_date,
                        "agent": nom_data.get("agent") or False,
                        "transporter": self._get_or_create_company(
                            nom_data.get("transporter")
                        ),
                        "receiver": self._get_or_create_company(
                            nom_data.get("receiver")
                        ),
                        "sender": self._get_or_create_company(nom_data.get("sender")),
                        "nomination_type": nom_data.get("nomination_type") or "",
                        "sample_required": bool(survey.get("sample_required")),
                        "inspection_before": bool(survey.get("inspection_before")),
                        "inspection_after": bool(survey.get("inspection_after")),
                        "certificate_of_analysis": bool(
                            survey.get("certificate_of_analysis")
                        ),
                        "references": ref_vals,
                        "product_transfers": pt_vals,
                    },
                )
            )

        extraction = (
            env["parser.extraction"]
            .sudo()
            .create(
                {
                    "job_id": job_id,
                    "email_from": data.get("from") or "",
                    "subject": data.get("subject") or "",
                    "nominations_summary": data.get("nominations_summary") or "",
                    "companies_summary": data.get("companies_summary") or "",
                    "nominations": nominations_vals,
                }
            )
        )
        return extraction
