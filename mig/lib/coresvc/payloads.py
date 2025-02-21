from collections import defaultdict, namedtuple

from mig.shared.safeinput import validate_helper


def _is_not_none(value):
    """value is not None"""
    assert value is not None, _is_not_none.__doc__


def _is_string_and_non_empty(value):
    """value is a non-empty string"""
    assert isinstance(value, str) and len(value) > 0, _is_string_and_non_empty.__doc__


class _FieldOnError:
    def __init__(self, field):
        self._field = field

    def replace(self, _, __):
        return self._field


def _define_payload(payload_name, payload_fields, validators_by_field):
    class Payload(namedtuple('PostUserArgs', payload_fields)):
        VALIDATORS = validators_by_field

        def keys(self):
            return Payload._fields

        def items(self):
            return self._asdict().items()

        @classmethod
        def to_checks(cls):
            value_checks = cls.VALIDATORS

            type_checks = {}
            for key in cls._fields:
                type_checks[key] = lambda _: None

            return type_checks, value_checks

    Payload.__name__ = payload_name

    return Payload


class ValidationReport(RuntimeError):
    def __init__(self, errors_by_field):
        self.errors_by_field = errors_by_field

    def serialize(self, output_format='text'):
        if output_format == 'json':
            return dict(errors=self.errors_by_field)
        else:
            lines = ["- %s: required %s" %
                     (k, v) for k, v in self.errors_by_field.items()]
            lines.insert(0, '')
            return 'payload failed to validate:%s' % ('\n'.join(lines),)


def validate_payload(definition, payload):
    args = definition(*[payload.get(field, _FieldOnError(field))
                      for field in definition._fields])
    fields = definition._fields
    type_checks, value_checks = definition.to_checks()

    _, errors_by_field = validate_helper(
        args._asdict(), fields, type_checks, value_checks, list_wrap=True)

    if errors_by_field:
        raise ValidationReport(errors_by_field)

    return args


PAYLOAD_POST_USER = _define_payload('PostUserArgs', [
    'full_name',
    'organization',
    'state',
    'country',
    'email',
    'comment',
    'password',
], defaultdict(lambda: _is_not_none, dict(
    full_name=_is_string_and_non_empty,
    organization=_is_string_and_non_empty,
    state=_is_string_and_non_empty,
    country=_is_string_and_non_empty,
    email=_is_string_and_non_empty,
    comment=_is_string_and_non_empty,
    password=_is_string_and_non_empty,
)))
