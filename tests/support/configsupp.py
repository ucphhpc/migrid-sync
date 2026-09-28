#
# --- BEGIN_HEADER ---
#
# configsupp - configuration helpers for unit tests
# Copyright (C) 2003-2024  The MiG Project by the Science HPC Center at UCPH
#
# This file is part of MiG.
#
# MiG is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# MiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Configuration related details within the test support library."""

from __future__ import annotations  # support of PEP 604 in Python 3.9

from collections.abc import Callable
from configparser import ConfigParser
from typing import Any, TextIO

from mig.shared.compat import SimpleNamespace
from mig.shared.configuration import (
    _CONFIGURATION_ARGUMENTS,
    _CONFIGURATION_PROPERTIES,
)
from tests.support.loggersupp import FakeLogger


def _ensure_only_configuration_keys(thedict):
    """Check a dictionary contains only keys valid as Configuration properties."""

    unknown_keys = set(thedict.keys()) - set(_CONFIGURATION_ARGUMENTS)
    assert len(unknown_keys) == 0, "non-Configuration keys: %s" % (
        ", ".join(unknown_keys),
    )


def _generate_namespace_kwargs():
    """Create plain dictionary with supported properties and keys that map to
    their default values suitable for use in fabricating a namespace.
    """

    properties_and_defaults = dict(_CONFIGURATION_PROPERTIES)
    properties_and_defaults["logger"] = None
    return properties_and_defaults


class FakeConfiguration(SimpleNamespace):
    """An object that can act as a representative Configuration which can be
    programmed with particular values required to exercise code under test.

    This object will track standard values as would be present on a genuine
    Configuration instance such that code under test expecting such can be
    handed something. The defaults are overlaid by any explicit keyword args.

    Automatically attaches a FakeLogger instance if no logger is provided in
    kwargs.
    """

    def __init__(self, logger=None, **kwargs):
        """Initialise instance attributes based on the defaults plus any
        supplied additional options.
        """

        SimpleNamespace.__init__(self, **_generate_namespace_kwargs())

        if logger is None:
            # TODO: remove this conditional once all callers that require a
            #       FakeConfiguration request it via _provide_configuration()
            logger = FakeLogger()
        self.logger = logger

        if kwargs:
            _ensure_only_configuration_keys(kwargs)
            for k, v in kwargs.items():
                setattr(self, k, v)

    def reload_config(self, *args, **kwargs):
        """Stub defined to quack like Configuration."""


def _ini_section_from_config(
    conf,
    attrs: list[str | tuple[str, Callable[[str], str]]],
    removeprefix: str | None = None,
) -> dict[str, Any]:
    """
    Create a dictionary containing ini-style configuration values,
    based on a configuration object.

    Args:
        conf: A configuration object.
        attrs: A list of configuration attributes to map the specific section's
            values. If an attribute is a string the attribute is mapped over
            directly (but the value is stringified) otherwise the given
            function is called on the configuration attribute.
        removeprefix: If given, remove the specified prefix from attribute names
            in the resulting ini section dictionary.

    Returns:
        A dictionary with the mapped configuration attributes.
    """
    ini = {}

    for key in attrs:
        conf_key = key
        ini_value = str

        if not isinstance(key, str):
            ini_value = key[1]
            conf_key = key[0]

        if not hasattr(conf, conf_key):
            continue

        ini_key = (
            conf_key.removeprefix(removeprefix) if removeprefix else conf_key
        )
        ini[ini_key] = ini_value(getattr(conf, conf_key))

    return ini


def write_configuration(conf, file: TextIO) -> None:
    """
    Write a serialized configuration file to the given file-like object
    opened in text mode.
    """

    config = ConfigParser()
    config["GLOBAL"] = _ini_section_from_config(
        conf,
        [
            "enable_server_dist",
            "auto_add_cert_user",
            "auto_add_oid_user",
            "auto_add_oidc_user",
            "auto_add_resource",
            "auto_add_user_permit",
            "auto_add_user_with_peer",
            "auto_add_filter_method",
            "auto_add_filter_fields",
            "server_fqdn",
            "support_email",
            "admin_email",
            ("admin_list", lambda v: ",".join(v)),
            "ca_fqdn",
            "ca_smtp",
            "ca_user",
            "jupyter_mount_files_dir",
            "mrsl_files_dir",
            "re_files_dir",
            "re_pending_dir",
            "log_dir",
            "re_home",
            "grid_stdin",
            "im_notify_stdin",
            "gridstat_files_dir",
            "mig_server_home",
            "mig_code_base",
            "resource_home",
            "resource_pending",
            "user_pending",
            "vgrid_home",
            "vgrid_files_home",
            "vgrid_files_readonly",
            "vgrid_files_writable",
            "vgrid_public_base",
            "vgrid_private_base",
            "user_home",
            "user_settings",
            "user_db_home",
            "user_cache",
            "user_messages",
            "server_home",
            "webserver_home",
            "sessid_to_mrsl_link_home",
            "sessid_to_jupyter_mount_link_home",
            "mig_system_files",
            "mig_system_storage",
            "mig_system_run",
            "wwwpublic",
            "server_cert",
            "server_key",
            "ca_cert",
            "freeze_home",
            "freeze_tape",
            "sharelink_home",
            "seafile_mount",
            "openid_store",
            "sitestats_home",
            "quota_home",
            "accounting_home",
            "public_key_file",
            "events_home",
            "twofactor_home",
            "gdp_home",
            "workflows_home",
            "workflows_db_home",
            "notify_home",
            "hg_path",
            "hgweb_scripts",
            "trac_admin_path",
            "trac_ini_path",
            "trac_id_field",
            "migserver_http_url",
            "migserver_https_url",
            "myfiles_py_location",
            "mig_server_id",
            "empty_job_name",
            "smtp_server",
            "smtp_sender",
            "smtp_send_as_user",
            "smtp_reply_to",
            "user_sftp_address",
            "user_sftp_port",
            "user_sftp_key",
            "user_sftp_key_pub",
            "user_sftp_key_md5",
            "user_sftp_key_sha256",
            "user_sftp_key_from_dns",
            "user_sftp_auth",
            "user_sftp_alias",
            "user_sftp_log",
            "user_sftp_subsys_address",
            "user_sftp_subsys_port",
            "user_sftp_subsys_log",
            "user_davs_address",
            "user_davs_port",
            "user_davs_key",
            "user_davs_key_sha256",
            "user_davs_auth",
            "user_davs_alias",
            "user_davs_log",
            "user_ftps_address",
            "user_ftps_ctrl_port",
            "user_ftps_pasv_ports",
            "user_ftps_key",
            "user_ftps_key_sha256",
            "user_ftps_auth",
            "user_ftps_alias",
            "user_ftps_log",
            "user_seahub_url",
            "user_seafile_url",
            "user_seafile_auth",
            "user_seafile_local_instance",
            "user_seafile_ro_access",
            "user_cloud_console_access",
            "user_cloud_ssh_auth",
            "user_cloud_alias",
            "user_imnotify_address",
            "user_imnotify_port",
            "user_imnotify_channel",
            "user_imnotify_username",
            "user_imnotify_password",
            "user_imnotify_log",
            "user_chkuserroot_log",
            "user_chksidroot_log",
            "user_openid_address",
            "user_openid_port",
            "user_openid_key",
            "user_openid_auth",
            "user_openid_alias",
            "user_openid_log",
            "user_openid_enforce_expire",
            "user_mig_oid_title",
            "user_ext_oid_title",
            "user_mig_oid_provider",
            "user_mig_oid_provider_alias",
            "user_ext_oid_provider",
            "user_openid_providers",
            "user_mig_oidc_title",
            "user_ext_oidc_title",
            "user_mig_oidc_provider",
            "user_ext_oidc_provider",
            "user_openidconnect_providers",
            "user_ext_oidc_issuer",
            "user_ext_oidc_audience",
            "user_mig_cert_title",
            "user_ext_cert_title",
            "user_monitor_log",
            "user_sshmux_log",
            "user_events_log",
            "user_cron_log",
            "user_janitor_log",
            "user_transfers_log",
            "user_notify_log",
            "user_auth_log",
            "user_shared_dhparams",
            "user_quota_log",
            "user_accounting_log",
            "logfile",
            "loglevel",
            "sleep_period_for_empty_jobs",
            "cputime_for_empty_jobs",
            "min_seconds_between_live_update_requests",
            "architectures",
            "scriptlanguages",
            "jobtypes",
            "lrmstypes",
        ],
    )
    config["SITE"] = _ini_section_from_config(
        conf,
        [
            "site_enable_migadmin",
        ],
        removeprefix="site_",
    )
    config["SCHEDULER"] = _ini_section_from_config(
        conf,
        [
            "algorithm",
            "expire_after",
            "job_retries",
        ],
    )
    config["MONITOR"] = _ini_section_from_config(
        conf,
        [
            "sleep_secs",
            "sleep_update_totals",
            "slackperiod",
        ],
    )
    config["SETTINGS"] = _ini_section_from_config(
        conf,
        [
            "language",
            "user_interface",
            "submitui",
        ],
    )
    config["FEASIBILITY"] = _ini_section_from_config(
        conf,
        [
            "resource_seen_within_hours",
            "skip_validation",
            "job_cond_green",
            "job_cond_yellow",
            "job_cond_orange",
            "job_cond_red",
            "enable_suggest",
            "suggest_threshold",
        ],
    )
    config["WORKFLOWS"] = _ini_section_from_config(
        conf,
        [
            "vgrid_tasks_home",
            "vgrid_patterns_home",
            "vgrid_recipes_home",
            "vgrid_history_home",
        ],
    )
    config["QUOTA"] = _ini_section_from_config(
        conf,
        [
            "backend",
            "update_interval",
            "user_limit",
            "vgrid_limit",
        ],
    )
    config["ACCOUNTING"] = _ini_section_from_config(conf, ["update_interval"])
    config["TEMPLATES"] = _ini_section_from_config(
        conf, ["base_packages", "cache_dir"]
    )
    config.write(file)
