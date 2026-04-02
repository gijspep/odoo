import base64
import json
import logging
import os

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
# In a multi-worker deployment each worker unlocks independently,
# but all workers read the same EMAIL_PARSER_KEY_PASSWORD env var so
# auto-unlock is transparent.
_cached_key: bytes | None = None

COMPANY_UID = "9F6C2A48-7B1E-4D3B-AE42-1C8E7F4A0D95"
EXTERNAL_API = "http://localhost:8000"


def _try_auto_unlock() -> None:
    """If EMAIL_PARSER_KEY_PASSWORD is set and the key is not yet cached,
    attempt to decrypt and cache it. Called lazily on the first request
    that needs the key, so request.env is available."""
    global _cached_key
    if _cached_key is not None:
        return
    password = os.environ.get("EMAIL_PARSER_KEY_PASSWORD")
    if not password:
        return
    try:
        _cached_key = _load_and_decrypt(password)
        _logger.info("email_parser: AES key auto-unlocked via environment variable")
    except Exception:
        _logger.warning(
            "email_parser: auto-unlock failed (wrong password or no key configured)"
        )


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
    def portal_landing_page(self, view="upload", id=None, **kwargs):
        _try_auto_unlock()
        key_set = bool(request.env["parser.api_key"].sudo().search([], limit=1))
        ctx = {
            "key_unlocked": _cached_key is not None,
            "key_set": key_set,
            "csrf_token": request.csrf_token(),
            "current_view": view,
        }

        if _cached_key is not None and key_set:
            env = request.env
            if view == "extractions":
                ctx["extractions"] = (
                    env["parser.extraction"].sudo().search([], order="id desc")
                )
            elif view == "extraction" and id:
                try:
                    rec = env["parser.extraction"].sudo().browse(int(id))
                    ctx["extraction"] = rec if rec.exists() else None
                except (ValueError, TypeError):
                    ctx["extraction"] = None
            elif view == "nominations":
                ctx["nominations"] = (
                    env["parser.nomination"].sudo().search([], order="id desc")
                )
            elif view == "nomination" and id:
                try:
                    rec = env["parser.nomination"].sudo().browse(int(id))
                    ctx["nomination"] = rec if rec.exists() else None
                except (ValueError, TypeError):
                    ctx["nomination"] = None

        return request.render(
            "email_parser.standalone_portal_template",
            ctx,
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
        _try_auto_unlock()
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
        _try_auto_unlock()
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
            files_data.append(
                {
                    "fileName": f.filename,
                    "fileType": ext,
                    "contentType": mime,
                    "content": content,
                }
            )

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
        _try_auto_unlock()
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

    # ── Draft confirmation ────────────────────────────────────────────────────

    @http.route(
        "/email_parser/confirm/<int:extraction_id>",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=True,
    )
    def confirm_extraction(self, extraction_id, **kwargs):
        extraction = request.env["parser.extraction"].sudo().browse(extraction_id)
        if not extraction.exists():
            return Response(
                json.dumps({"error": "Extraction not found."}),
                status=404,
                content_type="application/json",
            )
        if extraction.state != "draft":
            return Response(
                json.dumps({"error": "Extraction is already confirmed."}),
                status=400,
                content_type="application/json",
            )
        extraction.state = "confirmed"
        return request.redirect(f"/email_parser?view=extraction&id={extraction_id}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    # Words stripped from ship names and identifiers when normalising for matching.
    # Applied regardless of position (prefix, suffix, or middle word).
    _SHIP_NOISE = frozenset(
        {"ship", "barge", "vessel", "mt", "mv", "ms", "tanker", "boat", "motor"},
    )
    _ID_NOISE = frozenset({"eni", "imo"})

    def _normalize_ship_name(self, name):
        words = (name or "").lower().split()
        return " ".join(w for w in words if w not in self._SHIP_NOISE).strip()

    def _normalize_identifier(self, identifier):
        parts = (identifier or "").lower().split()
        return " ".join(p for p in parts if p not in self._ID_NOISE).strip()

    def _save_previous_cargoes(self, extraction, cargoes_data):
        if not cargoes_data:
            return

        # Build lookup: normalised_key -> {(modality_id, side, pt_id)}
        # Only SHIP modalities are considered for matching.
        lookup = {}
        for nom in extraction.nominations:
            for pt in nom.product_transfers:
                for side, modality in [
                    ("source", pt.source_modality),
                    ("destination", pt.destination_modality),
                ]:
                    if not modality or modality.modality_type != "SHIP":
                        continue
                    if modality.ship_name:
                        key = self._normalize_ship_name(modality.ship_name)
                        if key:
                            lookup.setdefault(key, set()).add(
                                (modality.id, side, pt.id),
                            )
                    if modality.identifier:
                        key = self._normalize_identifier(modality.identifier)
                        if key:
                            lookup.setdefault(key, set()).add(
                                (modality.id, side, pt.id),
                            )

        env = request.env["parser.previous_cargo"].sudo()
        for cargo in cargoes_data:
            ship_name = cargo.get("ship_name") or ""
            identifier = cargo.get("identifier") or ""
            common_vals = {
                "tank_id": cargo.get("tank_id") or "",
                "first_last": cargo.get("first_last") or "",
                "second_last": cargo.get("second_last") or "",
                "third_last": cargo.get("third_last") or "",
            }

            matches = set()
            if ship_name:
                matches |= lookup.get(self._normalize_ship_name(ship_name), set())
            if identifier:
                matches |= lookup.get(self._normalize_identifier(identifier), set())

            if matches:
                for modality_id, side, pt_id in matches:
                    # --- DYNAMICALLY DETERMINE THE FIELD NAME ---
                    transfer_key = (
                        "source_transfer_id"
                        if side == "source"
                        else "destination_transfer_id"
                    )
                    env.create(
                        {
                            **common_vals,
                            "modality_id": modality_id,
                            transfer_key: pt_id,
                        },
                    )
            else:
                name_parts = [p for p in [ship_name, identifier] if p]
                env.create(
                    {
                        **common_vals,
                        "unmatched_name": " / ".join(name_parts),
                        "extraction_id": extraction.id,
                    },
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

        # Cache model environments for cleaner code
        modality_env = env["parser.modality"].sudo()
        company_env = env["parser.company"].sudo()

        nominations_vals = []
        for nom_data in data.get("nominations") or []:
            pt_vals = []
            for pt_data in nom_data.get("product_transfers") or []:
                # --- THIS IS THE NEW, CLEAN LOGIC ---
                source_id = modality_env.get_or_create_from_api(
                    pt_data.get("source_modality"),
                )
                dest_id = modality_env.get_or_create_from_api(
                    pt_data.get("destination_modality"),
                )
                # ------------------------------------

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
                    ),
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
                        "agent": company_env.create({"name": n}).id
                        if (n := nom_data.get("agent"))
                        else False,
                        "transporter": company_env.create({"name": n}).id
                        if (n := nom_data.get("transporter"))
                        else False,
                        "receiver": company_env.create({"name": n}).id
                        if (n := nom_data.get("receiver"))
                        else False,
                        "sender": company_env.create({"name": n}).id
                        if (n := nom_data.get("sender"))
                        else False,
                        "nomination_type": nom_data.get("nomination_type") or "",
                        "sample_required": bool(survey.get("sample_required")),
                        "inspection_before": bool(survey.get("inspection_before")),
                        "inspection_after": bool(survey.get("inspection_after")),
                        "certificate_of_analysis": bool(
                            survey.get("certificate_of_analysis"),
                        ),
                        "references": ref_vals,
                        "product_transfers": pt_vals,
                    },
                ),
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
                    "previous_cargoes_summary": data.get("previous_cargoes_summary")
                    or "",
                    "state": "draft",
                    "nominations": nominations_vals,
                },
            )
        )
        self._save_previous_cargoes(extraction, data.get("previous_cargoes") or [])
        return extraction
