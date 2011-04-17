#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# notification - [insert a few words of module description on this line]
# Copyright (C) 2003-2009  The MiG Project lead by Brian Vinter
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,  MA 02110-1301, USA.
#
# -- END_HEADER ---
#

"""Notification functions"""

import os
import smtplib
import threading
from urllib import quote

from shared.job import output_dir
from shared.settings import load_settings
from shared.validstring import is_valid_email_address

# might be python 2.4, without xml.etree
# ...in which case: better not configure usage_record_dir

try:
    from shared.usagerecord import UsageRecord
except Exception, err:
    pass


def create_notify_message(
    jobdict,
    myfiles_py_location,
    status,
    statusfile,
    configuration,
    ):

    header = ''
    txt = ''
    jobid = jobdict['JOB_ID']
    job_retries = jobdict.get('RETRIES', configuration.job_retries)

    var_dict = {'https_cert_url': configuration.migserver_https_cert_url,
                'jobid': jobid, 'retries': job_retries,
                'output_dir': output_dir,
                'site' : configuration.short_title}

    if status == 'SUCCESS':
        header = '%s JOB finished' % configuration.short_title
        txt += \
            '''
Your %(site)s job with JOB ID %(jobid)s has finished and full status is available at:
%(https_cert_url)s/cgi-bin/jobstatus.py?job_id=%(jobid)s

The job commands and their exit codes:
'''\
             % var_dict
        try:
            status_fd = open(statusfile, 'r')
            txt += str(status_fd.read())
            status_fd.close()
        except Exception, err:
            txt += 'Could not be read (Internal error?): %s' % err
        txt += \
            '''
Link to stdout file:
%(https_cert_url)s/cert_redirect/%(output_dir)s/%(jobid)s/%(jobid)s.stdout (might not be available)

Link to stderr file:
%(https_cert_url)s/cert_redirect/%(output_dir)s/%(jobid)s/%(jobid)s.stderr (might not be available)

Replies to this message will not be read!
'''\
             % var_dict
    elif status == 'FAILED':

        header = '%s JOB Failed' % configuration.short_title
        txt += \
            '''
The job with JOB ID %(jobid)s has failed after %(retries)s retries!
This may be due to internal errors, but full status is available at:
%(https_cert_url)s/cgi-bin/jobstatus.py?job_id=%(jobid)s

Please contact the %(site)s team if the problem occurs multiple times.

Replies to this message will not be read!!!
'''\
             % var_dict
    elif status == 'EXPIRED':
        header = '%s JOB Expired' % configuration.short_title
        txt += \
            '''
Your %(site)s job with JOB ID %(jobid)s has expired, after remaining in the queue for too long.
This may be due to internal errors, but full status is available at:
%(https_cert_url)s/cgi-bin/jobstatus.py?job_id=%(jobid)s

Please contact the %(site)s team for details about expire policies.

Replies to this message will not be read!!!
'''\
             % var_dict
    elif status == 'SENDREQUEST':
        from_cert = myfiles_py_location[0]
        target_name = myfiles_py_location[1]
        request_type = myfiles_py_location[2]
        request_text = myfiles_py_location[3]
        reply_to = myfiles_py_location[4]
        entity = request_type.replace('vgrid', '').replace('resource', '')
        if request_type == "plain":
            header = '%s user message' % configuration.short_title
            txt += """This is a message sent on behalf of %s:

---

%s

---

""" % (from_cert, request_text)
        else:
            header = '%s %s request' % (configuration.short_title, request_type)
            txt += \
                """This is a %s request from %s who would like to be added to
'%s'
""" % (request_type, from_cert, target_name)
            if request_text:
                txt += '''The following reason was submitted by %s:
%s
''' % (from_cert, request_text)
            txt += \
                '''If you want to authorize this request visit the following
URL in a browser:
'''
            if request_type in ['vgridmember', 'vgridowner']:
                txt += \
                    '%s/cgi-bin/adminvgrid.py?vgrid_name=%s'\
                    % (configuration.migserver_https_cert_url, quote(target_name))
            elif request_type == 'resourceowner':
                txt += \
                    '%s/cgi-bin/resadmin.py?unique_resource_name=%s'\
                    % (configuration.migserver_https_cert_url, quote(target_name))
            else:
                txt += 'INVALID REQUEST TYPE: %s' % request_type
            txt += ' and add %s as %s.\n\n' % (from_cert, entity)
        txt += """IMPORTANT: direct replies to this message will not be read!!
        
If the message didn't include any contact information you may still be able to
reply using one of the message links for the user
%s
on your People page.
        """ % reply_to
    elif status == 'PASSWORDREMINDER':
        from_cert = myfiles_py_location[0]
        password = myfiles_py_location[1]
        header = '%s pasword reminder' % configuration.short_title
        txt += \
            """This is an auto generated password reminder from the %s server:
%s
""" % (configuration.short_title, password)
        txt += \
            """Feel free to locally change the password as described in the
user scripts tutorial online.
"""
        txt += """Replies to this message will not be read!!!"""
    else:
        header = '%s Unknown message type' % configuration.short_title
        txt += 'unknown status'
    return (header, txt)


def send_instant_message(
    recipients,
    protocol,
    header,
    message,
    logger,
    configuration,
    ):
    """Send message to recipients by IM through daemon. Please note
    that this function will *never* return if no IM daemon is running.
    Thus it must be forked/threaded if further actions are pending!
    """

    im_in_path = configuration.im_notify_stdin

    # <BR> used as symbol for newline, because newlines can not
    # be sent to the named pipe im_in_path directly.
    # TODO: Is <BR> a good symbol?.

    message = message.replace('\n', '<BR>')
    message = 'SENDMESSAGE %s %s %s: %s' % (protocol, recipients,
            header, message)
    logger.info('sending %s to %s' % (message, im_in_path))
    try:

        # This will block if no process is listening to im input pipe!!

        im_in_fd = open(im_in_path, 'a')
        im_in_fd.write(message + '\n')
        logger.info('%s written to %s' % (message, im_in_path))
        im_in_fd.close()
        return True
    except Exception, err:
        logger.error('could not get exclusive access or write to %s: %s %s'
                      % (im_in_path, message, err))
        print 'could not get exclusive access or write to %s!'\
             % im_in_path
        return False


def send_email(
    recipients,
    subject,
    message,
    logger,
    configuration,
    ):
    """Send message to recipients by email"""

    txt = '''From: %s
To: %s
Subject: %s

%s
'''\
         % (configuration.smtp_sender, recipients, subject, message)

    recipients_list = recipients.split(', ')

    try:
        server = smtplib.SMTP(configuration.smtp_server)
        server.set_debuglevel(0)
        errors = server.sendmail(configuration.smtp_sender,
                                 recipients_list, txt)
        server.quit()
        if errors:
            logger.warning('Partial error(s) sending email: %s'
                            % errors)
            return False
        else:
            logger.debug('Email was sent to %s' % recipients)
            return True
    except Exception, err:
        logger.error('Sending email to %s through %s failed!: %s'
                      % (recipients, configuration.smtp_server,
                     str(err)))
        return False


def notify_user(
    jobdict,
    myfiles_py_location,
    status,
    logger,
    statusfile,
    configuration,
    ):
    """Send notification messages about job to user. User settings are
    used if notification fields are left empty or set to 'SETTINGS'.
    Please note that this function may take a long time to deliver
    notifications, or even block forever if an IM is requested and no IM
    daemon is running. Thus it should be run in a separate thread or
    process if blocking is not allowed.
    Please take a look at notify_user_thread() if that is a requirement.
    """

    # Usage records: quickly hacked in here.
    # later, we might want a general plugin / hook interface

    # first of all, write out the usage record (if configured)

    ur_destination = configuration.usage_record_dir
    if ur_destination:

        logger.debug('XML Usage Record directory %s' % ur_destination)
        usage_record = UsageRecord(configuration, logger)
        usage_record.fill_from_dict(jobdict)

        # we use the job_id as a file name (should be unique)

        usage_record.write_xml(ur_destination + os.sep
                                + jobdict['JOB_ID'] + '.xml')

    jobid = jobdict['JOB_ID']
    for notify_line in jobdict['NOTIFY']:
        logger.debug('notify line: %s' % notify_line)
        (header, message) = create_notify_message(jobdict,
                myfiles_py_location, status, statusfile, configuration)

        supported_protocols = ['jabber', 'msn', 'icq', 'aol', 'yahoo']
        notify_line_colon_split = notify_line.split(':', 1)

        email_keyword_list = ['mail', 'email']

        if notify_line_colon_split[0].strip() in supported_protocols:
            protocol = notify_line_colon_split[0]
            recipients = notify_line_colon_split[1].strip()
            all_dest = []

            # Empty or

            if recipients.strip().upper() in ['SETTINGS', '']:

                # read from personal settings

                settings_dict = load_settings(jobdict['USER_CERT'],
                        configuration)
                if not settings_dict\
                     or not settings_dict.has_key(protocol.upper()):
                    logger.info('Settings dict does not have %s key'
                                 % protocol.upper())
                    continue
                all_dest = settings_dict[protocol.upper()]
            else:
                all_dest.append(recipients)
            for single_dest in all_dest:

                logger.debug('notifying %s about %s' % (single_dest,
                             jobid))

                # NOTE: Check removed because icq addresses are numbers and not "emails"
                # if not is_valid_email_address(single_dest, logger):
                # not a valid address (IM account names are on standard email format)
                # continue............................

                if send_instant_message(
                    single_dest,
                    protocol,
                    header,
                    message,
                    logger,
                    configuration,
                    ):
                    logger.info('Instant message sent to %s protocol: %s telling that %s %s'
                                 % (single_dest, protocol, jobid,
                                status))
                else:
                    logger.error('Instant message NOT sent to %s protocol %s jobid: %s'
                                  % (single_dest, protocol, jobid))
        else:
            notify_line_first_part = notify_line_colon_split[0].strip()
            all_dest = []
            if notify_line_first_part in email_keyword_list:
                logger.info("'%s' notify_line_first_part found in email_keyword_list"
                             % notify_line_first_part)
                recipients = notify_line.replace('%s: '
                         % notify_line_first_part, '').strip()
                if recipients.strip().upper() in ['SETTINGS', '']:

                    # read from personal settings

                    settings_dict = load_settings(jobdict['USER_CERT'],
                            configuration)
                    if not settings_dict:
                        logger.info('Could not load settings_dict')
                        continue
                    if not settings_dict.has_key('EMAIL'):
                        logger.info('Settings dict does not have EMAIL key'
                                    )
                        continue

                    all_dest = settings_dict['EMAIL']
                else:
                    all_dest.append(recipients)
            elif is_valid_email_address(notify_line, logger):
                all_dest.append(notify_line)

            # send mails

            for single_dest in all_dest:
                logger.info('email destination %s' % single_dest)

                # verify specified address is valid

                if not is_valid_email_address(single_dest, logger):
                    logger.info('%s is NOT a valid email address!'
                                 % single_dest)

                    # not a valid email address

                    continue

                if send_email(single_dest, header, message, logger,
                              configuration):
                    logger.info('email sent to %s telling that %s %s'
                                 % (single_dest, jobid, status))
                else:
                    logger.error('email NOT sent to %s, jobid: %s'
                                  % (single_dest, jobid))


    # logger.info("notify_user end")


def notify_user_thread(
    jobdict,
    myfiles_py_location,
    status,
    logger,
    statusfile,
    configuration,
    ):
    """Run notification in a separate thread to avoid delays or hangs
    in caller. Launches a new daemon thread to avoid waiting issues.
    We still must join thread if we want to assure delivery.
    """

    notify_thread = threading.Thread(target=notify_user, args=(
        jobdict,
        myfiles_py_location,
        status,
        logger,
        statusfile,
        configuration,
        ))
    notify_thread.setDaemon(True)
    notify_thread.start()
    return notify_thread


def send_resource_create_request_mail(
    client_id,
    hosturl,
    pending_file,
    logger,
    configuration,
    ):

    recipients = configuration.admin_email

    msg = "Sending the resource creation information for '%s' to '%s'"\
         % (hosturl, recipients)

    subject = '%s resource creation request on %s'\
         % (configuration.short_title, configuration.server_fqdn)
    txt = \
        """
Cert. ID: '%s'

Hosturl: '%s'

Configfile: '%s'

Resource creation command to run from mig/server/ directory:
./createresource.py '%s' '%s' '%s'
"""\
         % (
        client_id,
        hosturl,
        pending_file,
        hosturl,
        client_id,
        os.path.basename(pending_file),
        )

    status = send_email(recipients, subject, txt, logger, configuration)
    if status:
        msg += '\nEmail was sent to admins'
    else:
        msg += '\nEmail could not be sent to one or more recipients!'
    return (status, msg)


def parse_im_relay(path):
    """Parse path name and contents in order to generate
    message parameters for send_instant_message. This is
    used for IM relay support.
    """

    status = ''
    filename = os.path.basename(path)
    protocol = filename.lower().replace('.imrelay', '')
    (address, header, msg) = ('', '', '')
    try:

        # Parse message (address\nheader\nmsg)

        im_fd = open(path, 'r')
        address = im_fd.readline().strip()
        header = im_fd.readline().strip()
        msg = im_fd.read()
        im_fd.close()
        if not (protocol and address and header and msg):
            status += 'Invalid contents: %s;%s;%s;%s' % (protocol,
                    address, header, msg)
    except StandardError, err:
        status += 'IM relay parsing failed: %s' % err

    return (status, protocol, address, header, msg)


