from collections import defaultdict, namedtuple, OrderedDict

from mig.shared.safeinput import validate_helper


_EMPTY_LIST = {}
_REQUIRED_FIELD = object()


def _is_not_none(value):
    """value is not None"""
    assert value is not None, _is_not_none.__doc__


def _is_string_and_non_empty(value):
    """value is a non-empty string"""
    assert isinstance(value, str) and len(value) > 0, _is_string_and_non_empty.__doc__


class PayloadException(ValueError):
    def __str__(self):
        return self.serialize(output_format='text')

    def serialize(self, output_format='text'):
        error_message = self.args[0]

        if output_format == 'json':
            return dict(error=error_message)
        else:
            return error_message


class PayloadReport(PayloadException):
    def __init__(self, errors_by_field):
        self.errors_by_field = errors_by_field

    def serialize(self, output_format='text'):
        if output_format == 'json':
            return dict(errors=self.errors_by_field)
        else:
            lines = ["- %s: %s" %
                     (k, v) for k, v in self.errors_by_field.items()]
            lines.insert(0, '')
            return 'payload failed to validate:%s' % ('\n'.join(lines),)


class _MissingField:
    def __init__(self, field, message=None):
        assert message is not None
        self._field = field
        self._message = message

    def replace(self, _, __):
        return self._field

    @classmethod
    def assert_not_instance(cls, value):
        assert not isinstance(value, cls), value._message


class Payload(OrderedDict):
    def __init__(self, definition, dictionary):
        super(Payload, self).__init__(dictionary)
        self._definition = definition

    @property
    def _fields(self):
        return self._definition._fields

    @property
    def name(self):
        return self._definition._definition_name

    def __iter__(self):
        return iter(self.values())

    def items(self):
        return zip(self._definition._item_names, self.values())

    @staticmethod
    def define(payload_name, payload_fields, validators_by_field):
        positionals = list((field, validators_by_field[field]) for field in payload_fields)
        return PayloadDefinition(payload_name, positionals)


class PayloadDefinition:
    def __init__(self, name, positionals=_EMPTY_LIST):
        self._definition_name = name
        self._expected_positions = 0
        self._item_checks = []
        self._item_names = []

        if positionals is not _EMPTY_LIST:
            for positional in positionals:
                self._define_positional(positional)

    @property
    def _fields(self):
        return self._item_names

    def __call__(self, *args):
        return self._extract_and_bundle(args, extract_by='position')

    def _define_positional(self, positional):
        assert len(positional) == 2

        name, validator_fn = positional

        self._item_names.append(name)
        self._item_checks.append(validator_fn)

        self._expected_positions += 1

    def _extract_and_bundle(self, args, extract_by=None):
        definition = self

        if extract_by == 'position':
            actual_positions = len(args)
            expected_positions = definition._expected_positions
            if actual_positions < expected_positions:
                raise PayloadException('Error: too few arguments given (expected %d got %d)' % (
                    expected_positions, actual_positions))
            positions = list(range(actual_positions))
            dictionary = {definition._item_names[position]: args[position] for position in positions}
        elif extract_by == 'name':
            dictionary = {key: args.get(key, None) for key in definition._item_names}
        else:
            raise RuntimeError()

        return Payload(definition, dictionary)

    def ensure(self, bundle_or_args):
        bundle_definition = self

        if isinstance(bundle_or_args, Payload):
            assert bundle_or_args.name == bundle_definition._definition_name
            return bundle_or_args
        elif isinstance(bundle_or_args, dict):
            bundle = self._extract_and_bundle(bundle_or_args, extract_by='name')
        else:
            bundle = bundle_definition(*bundle_or_args)

        return _validate_bundle(self, bundle)

    def ensure_bundle(self, bundle_or_args):
        return self.ensure(bundle_or_args)

    def to_checks(self):
        type_checks = {}
        for key in self._fields:
            type_checks[key] = _MissingField.assert_not_instance

        value_checks = dict(zip(self._item_names, self._item_checks))

        return type_checks, value_checks


def _extract_field_error(bad_value):
    try:
        message = bad_value[0][1]
        if not message:
            raise IndexError
        return message
    except IndexError:
        return 'required'


def _prepare_validate_helper_input(definition, payload):
    def _covert_field_value(payload, field):
        value = payload.get(field, _REQUIRED_FIELD)
        if value is _REQUIRED_FIELD:
            return _MissingField(field, 'required')
        if value is None:
            return _MissingField(field, 'missing')
        return value
    return {field: _covert_field_value(payload, field)
            for field in definition._fields}


def _validate_bundle(definition, payload):
    assert isinstance(payload, Payload)

    input_dict = _prepare_validate_helper_input(definition, payload)
    type_checks, value_checks = definition.to_checks()
    _, bad_values = validate_helper(input_dict, definition._fields,
        type_checks, value_checks, list_wrap=True)

    if bad_values:
        errors_by_field = {field_name: _extract_field_error(bad_value)
                           for field_name, bad_value in bad_values.items()}
        raise PayloadReport(errors_by_field)

    return payload


PAYLOAD_POST_USER = Payload.define('PostUserArgs', [
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
