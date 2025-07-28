from flask import Blueprint, request, current_app

from mig.lib.coresvc.payloads import PayloadException, PAYLOAD_POST_USER
from mig.lib.coresvc.respond import \
    http_error_from_status_code, \
    json_reponse_from_status_code
from mig.shared.base import canonical_user, keyword_auto, force_native_str_rec
from mig.shared.useradm import fill_user, \
    create_user as useradm_create_user, search_users as useradm_search_users

def _create_user(configuration, payload):
    user_dict = canonical_user(
        configuration, payload, PAYLOAD_POST_USER._fields)
    fill_user(user_dict)
    force_native_str_rec(user_dict)

    try:
        useradm_create_user(user_dict, configuration, keyword_auto, default_renew=True)
    except:
        raise http_error_from_status_code(500, None)
    user_email = user_dict['email']
    objects = search_users(configuration, {
        'email': user_email
    })
    if len(objects) != 1:
        raise http_error_from_status_code(400, None)
    return objects[0]


def search_users(configuration, search_filter):
    _, hits = useradm_search_users(search_filter, configuration, keyword_auto)
    return list((obj for _, obj in hits))


bp = Blueprint('user', __name__)


@bp.get('/user')
def GET_user():
    raise http_error_from_status_code(400, None)

@bp.get('/user/<username>')
def GET_user_username(username):
    return 'FOOBAR'

@bp.get('/user/find')
def GET_user_find():
    configuration, = current_app.migctx
    query_params = request.args

    objects = search_users(configuration, {
        'email': query_params['email']
    })

    if len(objects) != 1:
        raise http_error_from_status_code(404, None)

    return dict(objects=objects)

@bp.post('/user')
def POST_user():
    configuration, = current_app.migctx
    payload = request.get_json()

    try:
        payload = PAYLOAD_POST_USER.ensure(payload)
    except PayloadException as vr:
        return http_error_from_status_code(400, None, vr.serialize())

    user = _create_user(configuration, payload)
    return json_reponse_from_status_code(201, user)
