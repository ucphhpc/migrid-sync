#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# --- BEGIN_HEADER ---
#
# sssfaq - SSS frequently asked questions
# Copyright (C) 2003-2016  The MiG Project lead by Brian Vinter
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
from __future__ import absolute_import

from mig.shared import returnvalues
from mig.shared.functional import validate_input
from mig.shared.init import initialize_main_variables

default_language = 'english'


def signature():
    """Signature of the main function"""

    defaults = {'language': [default_language]}
    return ['html_form', defaults]


html = {}
html['maintenance'] = \
    """
Sorry we are currently down for maintenance, we'll be back shortly
"""

html['english'] = \
    """
<table border='0' width='80%%' align='center'>
<tr><td><a class='danishlink iconspace' href='sssfaq.py?language=danish'>P&aring; dansk</a></td></tr>
<tr><td><h3>What happens when the screen saver deactivates?</h3></td></tr>
<tr><td>The sandbox is shut down and all hardware resources are given back to you. Any running job within the sandbox is killed and will eventually be scheduled for another resource by the %(site)s system. Work on suspending the job and sending it to another resource that can continue from where the job was suspended is in progress.</td></tr>

<tr><td><h3>Is the sandbox running correctly?</h3></td></tr>
<tr><td>If you don't get any error messages, you can assume that the sandbox is running correctly. After a while, you can login at the login-site and see the number of jobs that have been executed.</td></tr>

<tr><td><h3>What kind of jobs will be running on my computer?</h3></td></tr>
<tr><td>Frankly, we don't know. Anybody with a valid %(site)s user certificate can submit jobs that may end up in your sandbox, and smaller projects are typically quite transient. Many researchers from many different research areas use the system. However, we do know some projects that have been running for a while now on the sandboxes, and project homepages for each project will be available soon.</td></tr>

<tr><td><h3>Can the screen saver show what type of job is running in the sandbox?</h3></td></tr>
<tr><td>Your computer acts as a host system for the guest system that runs grid applications. The guest system runs in a sandbox, a virtual machine. There is no way for the two to interact; the grid job running in the guest system is not even aware of the fact that it is not running natively on a real physical machine, and the host system sees the virtual machine as any other user process. Hence, the screen saver which runs on the host system cannot know what is running inside the guest system. </td></tr>

<tr><td><h3>Which job is currently running on my machine?</h3></td></tr>
<tr><td>Anonymity between the users who submit jobs and the resource providers who donate the computing power is a key issue in the %(site)s design. Users do not know where their jobs will be executed, and resource owners do not know any details about the jobs their computer will execute. %(site)s keeps track of all jobs and resources, however, so in the event of abuse we can and will hold the misbehaving individuals responsible</td></tr>

<tr><td><h3>How much time do the jobs need to complete?</h3></td></tr>
<tr><td>It varies. It is up to the user to make sure that the jobs are suited for the screen saver model. We recommend below 60 minutes.</td></tr>

<tr><td><h3>Will this program eat my entire internet connection?</h3></td></tr>
<tr><td>No. By default, sandboxes will only download jobs and input files at max 256 kB/s and upload result files at max 128 kB/s, and you can set these appropriately when you download the sandbox. Further, the sandbox model only applies to small jobs that don't need to access big files.</td></tr>

<tr><td><h3>How do I see how many jobs I've executed?</h3></td></tr>
<tr><td>If you login to the download site, you'll see a list of your resources and the number of jobs executed by each of them. Alternatively you may take a look at the <a class='monitorlink iconspace' href='sssmonitor.py'>overall sandbox monitor</a>. Work is in progress on a credential system which will give a better presentation of user credits. </td></tr>

<tr><td><h3>Can the sandbox function behind a firewall/router/switch?</h3></td></tr>
<tr><td>Yes, however, some firewalls block individual applications in which case it is necessary to unblock the sandbox application, Qemu. Apart from that, the sandbox only uses standard protocols (HTTP and HTTPS) that are normally open for outbound access, and all communication is initiated by the sandbox, i.e. the Grid system never contacts the sandbox, since this would not be possible had the sandbox resided behind an NAT router.</td></tr>

<tr><td><h3>What's the difference between the screen saver and the Windows service model?</h3></td></tr>
<tr><td>The screen saver model ensures that the computer is only working on Grid jobs when the screen saver is activated. This model is installed by default. In the Windows Service model, the sandbox is running constantly in the background whenever the computer is on. Note that this model requires administrator privileges to install the service. If you choose to install the Service model, the screen saver will not be activated. </td></tr>

<tr><td><h3>How is this projet different from other @home projects such as seti@home, folding@home, etc.?</h3></td></tr>
<tr><td>The existing @home projects are not true grid computing but merely one-way systems to which you can only donate your machine to a specific research project. In %(site)s, any user of the system can submit a job without porting it to a specific framework. Further, as the @home clients will execute the applications natively on your computer, they can, theoretically, compromise your computer.<td><tr>


<!-- question template: 
<tr><td><h3></h3></td></tr>
<tr><td></td></tr>
-->

<tr><td><a class='backlink iconspace' href='ssslogin.py?language=english'>Back to Sandbox login page</a></td></tr>

</table>
<br />
"""

html['danish'] = \
    """
<table border='0' width='80%%' align='center'>
<tr><td><a class='englishlink iconspace' href='sssfaq.py?language=english'>In English</a></td></tr>
<tr><td><h3>Intro</h3></td></tr>
<tr><td>Velkommen til %(site)s-SSS. Ved at downloade og installere denne software vil din PC, n&aring;r screensaveren er aktiv, donere overskydende regnekraft til l&oslash;sning af videnskabelige problemer. Det eneste, der kr&aelig;ves er, at man logger ind, downloader softwaren og f&oslash;lger installationsproceduren.<td><tr>

<tr><td>
<tr><td><h3>Hvad sker der n&aring; screen-saveren stopper?</h3></td></tr>
<tr><td>Sandkassen stoppes og alle de hardware resurser den har reserveret frigives til dig igen n&aring;r screen-saveren stopper. Eventuelt igangv&aelig;rende jobs i sandkassen lukkes ned og bliver med tiden sendt ud til en ny resurse og k&oslash;rt forfra af %(site)s systemet. Arbejde p&aring; at suspendere/pause jobs s&aring; de direkte kan k&oslash;re videre p&aring; en anden resurse er igang.</td></tr>

<tr><td><h3>K&oslash;rer sandkassen kkorrekt?</h3></td></tr>
<tr><td>Medmindre du f&aring;r fejlbeskeder, kan du regne med at sandkassen fungerer som den skal. N&aring;r sandkassen har k&oslash;rt et stykke tid kan du g&aring; ind p&aring; sandkasse login-siden og f&oslash;lge med i hvor mange jobs den har k&oslash;rt.</td></tr>

<tr><td><h3>Hvilken slags jobs k&oslash;rer p&aring; min computer?</h3></td></tr>
<tr><td>Dybest set ved vi det ikke. Hvem som helst med et gyldigt %(site)s bruger certifikat kan indsende jobs til at k&oslash;re p&aring; en vilk&aring;rlig sandkasse resurse, og mindre forskningsprojekter er typisk ret kortvarige. Mange forskere fra mange forskellige forskningsomr&aring;der benytter systemet til deres forskning. Vi uddeler ikke %(site)s bruger certifikater til hvem som helst, s&aring; du kan v&aelig;re sikker p&aring; at jobs i hvert fald bruges til samfundsgavnlig forskning. Vi h&aring;ber snarest at f&aring; nogle af de aktive grupper til at lave projektsider p&aring; nettet med yderligere informationer om - og baggrund for deres forskning, s&aring; den noget uklare beskrivelse kan konkretiseres.</td></tr>

<tr><td><h3>Kan screen-saveren vise hvilken slags job den k&oslash;rer i sandkassen?</h3></td></tr>
<tr><td>Din computer fungerer som et v&aelig;rtssystem for det g&aelig;stesystem, der k&oslash;rer grid applikationer. G&aelig;stesystemet k&oslash;rer i en sandkasse, en virtuel maskine. De to systemer har derfor ingen m&aring;de at interagere p&aring;; grid applikationen, som k&oslash;rer under g&aelig;stesystemet er faktisk slet ikke klar over at den ikke k&oslash;rer direkte p&aring; en fysisk computer, og v&aelig;rtssystemet ser bare den virtuelle maskine som en vilk&aring;lig anden program-process. Derfor kan screen-saveren p&aring; v&aelig;rtssystemet ikke vide hvad der k&oslash;rer inde i g&aelig;stesystemet.</td></tr>

<tr><td><h3>Hvilket job k&oslash;rer i &oslash;jeblikket p&aring; min computer?</h3></td></tr>
<tr><td>Anonymitet mellem brugere der indsender jobs og resurser der k&oslash;rer dem med deres overskydende regnekraft er et overordnet designvalg i %(site)s. S&aring; brugere ved som udgangspunkt ikke hvor deres jobs faktisk k&oslash;res og resurseejere kender ikke til ejerskabet for de enkelte jobs. %(site)s holder dog styr p&aring; alle jobs og resurser, s&aring; hvis nogen misbruger tilliden kan og vil de blive holdt til ansvar.</td></tr>

<tr><td><h3>Hvor l&aelig;nge tager jobs om at k&oslash;re f&aelig;rdige?</h3></td></tr>
<tr><td>Kort sagt er det meget forskelligt. Det overlades til den enkelte bruger at sikre at hendes jobs er egnede til at k&oslash;re i sandkasse-resurser, som kan komme og g&aring; uden varsel. Vi anbefaler derfor at brugere s&oslash;rger for at deres sandkassejobs g&oslash;r sig f&aelig;rdige indenfor 60 minutter. Hvis ikke de kan blive helt f&aelig;rdige p&aring; den tid, kan forskellige check pointing l&oslash;sninger overvejes, s&aring; et delresultat gemmes til at arbejde videre p&aring; senere .</td></tr>

<tr><td><h3>Vil sandkassen &aelig;de hele min internetforbindelse?</h3></td></tr>
<tr><td>Nej, som udgangspunkt henter sandkasser kun job- og input-filer med op til 256 kB/s og sender resultatfiler med op til 128 kB/s, og du kan skrue yderlige ned eller op p&aring; disse v&aelig;rdier n&aring;r du genererer og henter din sandkasse. Selv med de mindste ADSL l&oslash;sninger p&aring; markedet skulle standard-indstillingerne dog v&aelig;re uproblematiske. Yderligere er sandkasse-modellen hovedsageligt henvendt til sm&aring; jobs, der kan klare sig uden store datafiler, s&aring; overf&oslash;rslerne tager ikke lang tid.</td></tr>

<tr><td><h3>Hvordan ser jeg hvor mange jobs min sandkasse har k&oslash;rt?</h3></td></tr>
<tr><td>Hvis du &aring;bner sandkasse startsiden og logger ind, n&aring;r du frem til en monitor side med en liste over dine sandkasse-resurser og deres k&oslash;rte jobs. Du kan ogs&aring; se hvor meget dine sandkasser har ydet sammenlignet med andre brugeres  p&aring; den <a class='monitorlink iconspace' href='sssmonitor.py'>samlede sandkasse monitor</a>. Der arbejdes p&aring; at lave et mere finkornet opregning af hvad de enkelte resurser har leveret s&aring; det er lettere at sammenligne.</td></tr>

<tr><td><h3>Kan sandkasser fungere bag en firewall/router/switch?</h3></td></tr>
<tr><td>Ja, men nogle firewalls blokkerer individuelle applikationer, hvorfor det kan v&aelig;re n&oslash;dvendigt at tillade sandkasse applikationen, Qemu, at tilg&aring; internettet. Bortset fra det, benytter sandkassen kun standard protokoller (HTTP og HTTPS), som normalt i forvejen er tilladt for udg&aring;ende trafik, og al kommunikation initieres fra sandkassen. D.v.s. Grid systemet kontakter aldrig sandkassen men kun omvendt, da det ellers ikke ville v&aelig;re muligt at k&oslash;re sandkassen bag f.eks. en NAT router.</td></tr>

<tr><td><h3>Hvad er forskellen mellem screen-saver - og Windows service modellen?</h3></td></tr>
<tr><td>Screen-saver modellen sikrer at computeren kun tilbyder regnekraft til Grid jobs n&aring;r screen-saveren er aktiv. Det er den almindelige model, da det generer brugeren mindst muligt. I Windows Service modellen, k&oslash;rer sandkassen altid i baggrunden n&aring;r computeren er t&aelig;ndt. Det giver en mere effektiv resurse, da jobs s&aring; sj&aelig;ldent afbrydes, men det kr&aelig;ver administrator rettigheder at installere som en service og kan is&aelig;r p&aring; &aelig;ldre og mindre computere genere det daglige brug. Hvis du v&aelig;lger at installere Service modellen, vil screen-saveren ikke blive brugt.</td></tr>

<tr><td><h3>Hvordan adskiller %(site)s projektet sig fra andre projekter som seti@home, folding@home, o.s.v.?</h3></td></tr>
<tr><td>De eksisterende @home projekter er ikke &aelig;gte grid computing, men derimod 'kun' envejs systemer hvori du kan donere din overskydende regnekraft til et specifikt forskningsprojekt, som f&oslash;rst har tilpasset sin applikation til systemet. Det betyder bl.a. at det er mere arbejdskr&aelig;vende for en forsker at komme igang med at f&aring; sin forskningsapplikation k&oslash;rt. Med %(site)s kan en vilk&aring;rlig bruger derimod indsende jobs uden f&oslash;rst at skulle omskrive sit program til et givet system. Ydermere k&oslash;rer @home programmerne direkte p&aring; din computer, hvormed de teoretisk kan misbruge din computer.<td><tr>

<tr><td><a class='backlink iconspace' href='ssslogin.py?language=danish'>Tilbage til sandkasse login siden</a></td></tr>

</table>
<br />

</table></form>
"""


def main(client_id, user_arguments_dict):
    """Main function used by front end"""

    (configuration, logger, output_objects, op_name) = \
        initialize_main_variables(client_id, op_header=False,
                                  op_menu=client_id)
    output_objects.append({'object_type': 'header', 'text'
                          : '%s Screen Saver Sandbox FAQ' % \
                            configuration.short_title })
    defaults = signature()[1]
    (validate_status, accepted) = validate_input(user_arguments_dict,
            defaults, output_objects, allow_rejects=False)
    if not validate_status:
        return (accepted, returnvalues.CLIENT_ERROR)

    language = accepted['language'][-1]

    if not configuration.site_enable_sandboxes:
        output_objects.append({'object_type': 'text', 'text':
                               '''Sandbox resources are disabled on this site.
Please contact the site admins %s if you think they should be enabled.
''' % configuration.admin_email})
        return (output_objects, returnvalues.OK)

    if not language in html.keys():
        output_objects.append({'object_type': 'error_text', 'text'
                              : 'Unsupported language: %s, defaulting to %s'
                               % (language, default_language)})
        language = default_language

        # print "<a href='ssslogin.py'>Default language</a>"
        # sys.exit(1)
   # output_objects.append({"object_type":"html_form", "text":html[language]})

    output_objects.append({'object_type': 'html_form', 'text'
                          : html[language] % \
                           {'site': configuration.short_title}})
    return (output_objects, returnvalues.OK)


