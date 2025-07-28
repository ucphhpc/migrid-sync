from flask import Response
import json
import werkzeug.exceptions as httpexceptions

httpexceptions_by_code = {
    exc.code: exc for exc in httpexceptions.__dict__.values() if hasattr(exc, "code")
}


def http_error_from_status_code(http_status_code, http_url, description=None):
    return httpexceptions_by_code[http_status_code](description)


def json_reponse_from_status_code(http_status_code, content):
    json_content = json.dumps(content)
    return Response(
        json_content, http_status_code, {"Content-Type": "application/json"}
    )
