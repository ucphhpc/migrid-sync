#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sandbox_faq - [insert a few words of module description on this line]
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

"""This script is the welcome site for sandbox users"""

import sys
from shared.init import initialize_main_variables
from shared.functional import validate_input, REJECT_UNSET
import shared.returnvalues as returnvalues

default_language = 'english'


def signature():
    defaults = {'language': [default_language]}
    return ['html_form', defaults]


html = {}
html['maintenance'] = \
    """
Sorry we are currently down for maintenance, we'll be back shortly
"""

html['english'] = \
    """
<table border='0' width='80%' align='center'>
<tr><td><h3>What happens when the screen saver deactivates?</h3></td></tr>
<tr><td>The sandbox is shut down and all hardware resources are given back to you. Any running job within the sandbox is killed and will eventually be scheduled for another resource by the MiG system. Work on suspending the job and sending it to another resource that can continue from where the job was suspended is in progress.</td></tr>

<tr><td><h3>Is the sandbox running correctly?</h3></td></tr>
<tr><td>If you don't get any error messages, you can assume that the sandbox is running correctly. After a while, you can login at the login-site and see the number of jobs that have been executed.</td></tr>

<tr><td><h3>What kind of jobs will be running on my computer?</h3></td></tr>
<tr><td>Frankly, we don't know. Anybody with a valid MiG user certificate can submit jobs that may end up in your sandbox, and smaller projects are typically quite transient. Many researchers from many different research areas use the system. However, we do know some projects that have been running for a while now on the sandboxes, and project homepages for each project will be available soon.</td></tr>

<tr><td><h3>Can the screen saver show what type of job is running in the sandbox?</h3></td></tr>
<tr><td>Your computer acts as a host system for the guest system that runs grid applications. The guest system runs in a sandbox, a virtual machine. There is no way for the two to interact; the grid job running in the guest system is not even aware of the fact that it is not running natively on a real physical machine, and the host system sees the virtual machine as any other user process. Hence, the screen saver which runs on the host system cannot know what is running inside the guest system. </td></tr>

<tr><td><h3>Which job is currently running on my machine?</h3></td></tr>
<tr><td>Anonymity between the users who submit jobs and the resource providers who donate the computing power is a key issue in the MiG design. Users do not know where their jobs will be executed, and resource owners do not know any details about the jobs their computer will execute.</td></tr>

<tr><td><h3>How much time do the jobs need to complete?</h3></td></tr>
<tr><td>It varies. It is up to the user to make sure that the jobs are suited for the screen saver model. We recommend below 60 minutes.</td></tr>

<tr><td><h3>Will this program eat my entire internet connection?</h3></td></tr>
<tr><td>No. By default, sandboxes will only download jobs and input files at max 256 kB/s and upload result files at max 128 kB/s, and you can set these appropriately when you download the sandbox. Further, the sandbox model only applies to small jobs that don't need to access big files.</td></tr>

<tr><td><h3>How do I see how many jobs I've executed?</h3></td></tr>
<tr><td>If you login to the download site, you'll see a list of your resources and the number of jobs executed by each of them. There is a public sandbox monitor <a href='%s/cgi-bin/sandboxmonitor.py'>here</a>. Work is in progress on a credential system which will give a better presentation of user credits. </td></tr>

<tr><td><h3>Can the sandbox function behind a firewall/router/switch?</h3></td></tr>
<tr><td>Yes, however, some firewalls block individual applications in which case it is necessary to unblock VMWare Player. Apart from that, the sandbox only uses standard protocols (http+https) that are normally open for outbound access, and all communication is initiated by the sandbox, i.e. the Grid system never contacts the sandbox, since this would not be possible had the sandbox resided behind an NAT router.</td></tr>

<tr><td><h3>What's the difference between the screen saver and the Windows service model?</h3></td></tr>
<tr><td>The screen saver model ensures that the computer is only working on Grid jobs when the screen saver is activated. This model is installed by default. In the Windows Service model, the sandbox is running constantly in the background whenever the computer is on. Note that this model requires administrator privileges to install the service. If you choose to install the Service model, the screen saver will not be activated. </td></tr>

<tr><td><h3>How is this projet different from other @home projects such as seti@home, folding@home, etc.?</h3></td></tr>
<tr><td>The existing @home projects are not true grid computing but merely one-way systems to which you can only donate your machine to a specific research project. In MiG, any user of the system can submit a job without porting it to a specific framework. Further, as the @home clients will execute the applications natively on your computer, they can, theoretically, compromise your computer.<td><tr>


<!-- question template: 
<tr><td><h3></h3></td></tr>
<tr><td></td></tr>
-->

</table>
<br>

</table></form>
"""

html['danish'] = \
    """
<table border='0' width='80%' align='center'>
<tr><td><a href='sandbox_faq.py?language=english'>In English</a></td></tr>
<tr><td><h3>Intro</h3></td></tr>
<tr><td>Velkommen til MiG-SSS. Ved at downloade og installere denne software vil din PC, n&aring;r den er i screen saver mode, donere den ubrugte CPU-tid til at bidrage med at l&oslash;se videnskabelige problemer. Det eneste, der kr&aelig;ves er, at man logger ind nedenfor, downloader softwaren og f&oslash;lger installationsproceduren.<td><tr>

</table>
<br>

</table></form>
"""


def main(cert_name_no_spaces, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(op_header=False)
    output_objects.append({'object_type': 'header', 'text'
                          : 'MiG Screen Saver Sandbox FAQ'})

    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)
    language = accepted['language'][-1]

    if not language in html.keys():
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Unsupported language: %s, defaulting to %s'
                               % (language, default_language)})
        language = default_language

        # print "<a href='sandbox_login.py'>Default language</a>"
        # sys.exit(1)
#    output_objects.append({"object_type":"html_form", "text":html[language]})

    output_objects.append({'object_type': 'html_form', 'text'
                          : html['english'] % configuration.migserver_https_url})
    return (output_objects, returnvalues.OK)


