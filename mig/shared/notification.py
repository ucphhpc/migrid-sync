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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# -- END_HEADER ---
#

"""Notification functions"""

import os
import fcntl
import smtplib

from shared.validstring import is_valid_email_address
from shared.configuration import Configuration
from shared.fileio import unpickle


def notify_user(
    jobdict,
    myfiles_py_location,
    status,
    logger,
    statusfile,
    smtp_server,
    configuration,
    ):
    """Send notification messages about job to user. User settings are
    used if notification fields are left empty or set to 'SETTINGS'.
    """

    settings_dict_file = configuration.user_home + jobdict['USER_CERT']\
         + os.sep + '.settings'

    jobid = jobdict['JOB_ID']
    for notify_line in jobdict['NOTIFY']:
        logger.debug('notify line: %s', notify_line)
        (header, message) = create_notify_message(jobid,
                myfiles_py_location, status, statusfile, configuration)

        supported_protocols = ['jabber', 'msn', 'icq', 'aol', 'yahoo']
        notify_line_colon_split = notify_line.split(':', 1)

        email_keyword_list = ['mail', 'email']

        if notify_line_colon_split[0].strip() in supported_protocols:
            protocol = notify_line_colon_split[0]
            to = notify_line.replace('%s: ' % protocol, '').strip()
            all_dest = []

            # Empty or

            if to.strip().upper() in ['SETTINGS', '']:

        # read from personal settings

                settings_dict = unpickle(settings_dict_file, logger)
                if not settings_dict:
                    logger.info('Could not unpickle settings_dict %s'
                                 % settings_dict_file)
                    continue
                if not settings_dict.has_key(protocol.upper()):
                    logger.info('Settings dict does not have %s key'
                                 % protocol.upper())
                    continue

                all_dest = settings_dict[protocol.upper()]
            else:
                all_dest.append(to)
            for single_dest in all_dest:

        # NOTE: Check removed because icq addresses are numbers and not "emails"
        # if not is_valid_email_address(single_dest, logger):
            # not a valid address (IM account names are on standard email format)
            # continue............................

                if send_instant_message(single_dest, protocol, header,
                        message, logger):
                    logger.info('Instant message sent to %s protocol: %s telling that %s %s'
                                , single_dest, protocol, jobid, status)
                else:
                    logger.error('Instant message NOT sent to %s protocol %s jobid: %s'
                                 , single_dest, protocol, jobid)
        else:
            notify_line_first_part = notify_line_colon_split[0].strip()
            all_dest = []
            if notify_line_first_part in email_keyword_list:
                logger.info("'%s' notify_line_first_part found in email_keyword_list"
                             % notify_line_first_part)
                to = notify_line.replace('%s: '
                         % notify_line_first_part, '').strip()
                if to.strip().upper() in ['SETTINGS', '']:

            # read from personal settings

                    settings_dict = unpickle(settings_dict_file, logger)
                    if not settings_dict:
                        logger.info('Could not unpickle settings_dict %s'
                                     % settings_dict_file)
                        continue
                    if not settings_dict.has_key('EMAIL'):
                        logger.info('Settings dict does not have EMAIL key'
                                    )
                        continue

                    all_dest = settings_dict['EMAIL']
                else:
                    all_dest.append(to)
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

        # elif is_valid_email_address(notify_line, logger):
            # to = notify_line
            # else:
            # not a valid email address
            # continue

                if send_email(single_dest, header, message,
                              smtp_server, logger):
                    logger.info('email sent to %s telling that %s %s',
                                single_dest, jobid, status)
                else:
                    logger.error('email NOT sent to %s, jobid: %s',
                                 single_dest, jobid)


    # logger.info("notify_user end")


def create_notify_message(
    jobid,
    myfiles_py_location,
    status,
    statusfile,
    configuration,
    ):

    header = ''
    txt = ''

    if status == 'SUCCESS':
        header = 'MiG JOB finished'
        txt += \
            'Your MiG job with JOB ID %s has finished. Outputfiles can be found here: %s'\
             % (jobid, myfiles_py_location)
        txt += '''
The commands and exit codes:
'''
        try:
            fh = open(statusfile, 'r')
            txt += str(fh.read())
            fh.close()
        except Exception, err:
            txt += 'Could not be read. (Internal MiG error?)%s' % err
        txt += \
            '\nLink to stdout file: https://%s/cert_redirect/job_output/%s/%s.stdout (might not be available)'\
             % (configuration.server_fqdn, jobid, jobid)
        txt += \
            '\nLink to stderr file: https://%s/cert_redirect/job_output/%s/%s.stderr (might not be available)'\
             % (configuration.server_fqdn, jobid, jobid)
        txt += '\nReplies to this message will not be read!'
    elif status == 'FAILED':

        header = 'MiG JOB Failed'
        txt += \
            'The job with JOB ID %s has failed after %s retries, due to internal errors.'\
             % (jobid, configuration.job_retries)
        txt += '\nFor details use migstatus -v %s' % jobid
        txt += \
            '\nPlease contact the MiG team if the problem occurs multiple times.'
        txt += '''

Replies to this message will not be read!!!
'''
    elif status == 'EXPIRED':
        header = 'MiG JOB Expired'
        txt += \
            'Your MiG job with JOB ID %s has expired, after remaining in the queue for too long. Please contact the '\
             % jobid
        txt += ' MiG team for details about expire policies.\n'
        txt += 'Replies to this message will not be read!!!\n'
    elif status == 'VGRIDMEMBERREQUEST':
        from_cert = myfiles_py_location[0]
        vgrid_name = myfiles_py_location[1]
        request_type = myfiles_py_location[2]
        request_text = myfiles_py_location[3]
        header = 'MiG VGrid member request'
        txt += \
            "This is a request from %s who would like to be added to your VGrid '%s' as a %s\n"\
             % (from_cert, vgrid_name, request_type)
        if request_text:
            txt += '''The following reason was submitted by %s:
%s
'''\
                 % (from_cert, request_text)
        txt += \
            'If you want to authorize this request visit the following link in a browser: \n'
        if request_type == 'member':
            txt += \
                '%s/cgi-bin/addvgridmember.py?vgrid_name=%s&cert_name=%s'\
                 % (configuration.migserver_https_url, vgrid_name,
                    from_cert)
        elif request_type == 'owner':
            txt += \
                '%s/cgi-bin/addvgridowner.py?vgrid_name=%s&cert_name=%s'\
                 % (configuration.migserver_https_url, vgrid_name,
                    from_cert)
        else:
            txt += 'INVALID REQUEST TYPE: %s' % request_type

        txt += ' Replies to this message will not be read!!!\n'
    else:
        header = 'MiG Unknown message type'
        txt += 'unknown status'
    return (header, txt)


def send_instant_message(
    to,
    protocol,
    header,
    message,
    logger,
    ):

    try:

        # <BR> used as symbol for newline, because newlines can not
        # be sent to the named pipe stdin_path directly.
        # TODO: Is <BR> a good symbol?.

        message = message.replace('\n', '<BR>')
        message = 'SENDMESSAGE %s %s %s: %s' % (protocol, to, header,
                message)
        configuration = Configuration('../server/MiGserver.conf')
        stdin_path = configuration.im_notify_stdin
        fh = open(stdin_path, 'a')
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        fh.write(message + '\n')
        logger.info('%s written to %s' % (message, stdin_path))
        fh.close()
        return True
    except Exception, err:
        print 'could not get exclusive access or write to %s!'\
             % stdin_path
        logger.error('could not get exclusive access or write to %s: %s %s'
                      % (stdin_path, message, err))
        return False


def send_email(
    to,
    header,
    message,
    smtp_server,
    logger,
    ):

    txt = 'To: %s\n' % to
    txt += 'From: MiG_no_reply@imada.sdu.dk\n'
    txt += 'Subject: %s\n' % header
    txt += message
    sender = 'MiG_no_reply@imada.sdu.dk'

    if -1 != to.find(', '):
        to = to.split(', ')

    try:

        # This does not work on vcr atm (the line below throws an exception). It should work on mig-1?

        server = smtplib.SMTP(smtp_server)
        server.set_debuglevel(0)
        errors = server.sendmail(sender, to, txt)
        server.quit()
        if errors:
            logger.warning('Partial error(s) sending email: %s', errors)
            return False
        else:
            logger.debug('Email was sent to %s', to)
            return True
    except Exception, err:
        logger.error('Sending email to %s through %s failed!: %s', to,
                     smtp_server, str(err))
        return False


def send_resource_create_request_mail(
    cert_name_no_spaces,
    hosturl,
    pending_file,
    configuration,
    ):

    # ## TODO: Change this function to use the framework above!!

    recipients = configuration.admin_email
    smtp_server = configuration.smtp_server

    msg = "Sending the resource creation information for '%s' to '%s'"\
         % (hosturl, recipients)

    txt = 'To: ' + recipients + '\n'
    txt = txt + 'From: MiG_no_reply@imada.sdu.dk\n'

    txt = txt + 'Subject: MiG resource creation request.\n'
    txt = txt + """Cert. name: '%s'

""" % cert_name_no_spaces
    txt = txt + """Hosturl: '%s'

""" % hosturl
    txt = txt + """Configfile: '%s'

""" % pending_file
    txt = txt\
         + 'Resource creation command:\n./createresource.py %s %s %s'\
         % (hosturl, cert_name_no_spaces,
            pending_file[pending_file.rindex('/') + 1:])

    if -1 != recipients.find(', '):
        reciepients = recipients.split(', ')
    else:
        reciepients = recipients

    sender = 'MiG_no_reply@imada.sdu.dk'
    try:
        server = smtplib.SMTP(smtp_server)
        server.set_debuglevel(0)
        errors = server.sendmail(sender, reciepients, txt)
        server.quit()
        if errors:
            msg += '\nPartial error(s) sending email: %s' % errors
            return (False, msg)
        else:
            msg += "\nEmail was sent to '%s'" % recipients
            return (True, msg)
    except Exception, err:
        msg += "Sending email to '%s' through %s failed!: %s"\
             % (recipients, smtp_server, err)
        return (False, msg)


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


