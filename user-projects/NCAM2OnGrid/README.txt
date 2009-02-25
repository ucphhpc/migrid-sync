= Introduction =
The NCAM2 project is driven by Farma at University of Copenhagen and it
investigates structure and dynamics of neural cell adhesion molecule 2 (NCAM2).
As Farma are the experts on the molecular dynamics they take care of all the
work in that domain and only rely on us for the actual Grid execution.
The investigation mainly uses the AMBER software (http://ambermd.org/) to
simulate the molecular dynamics.


= Grid preparations =
The total amount of computations associated with the NCAM2 project is
significantly higher than what their local resources can provide in a
reasonable time frame, so they have been granted a so-called 'sandkasse'-slot
on the DCSC resources.
The individual simulations are CPU bound and single node multicore execution is
the most efficient approach. Each simulation requires only limited memory and
disk so most multi core resources will do.
AMBER is not free software but we have received permission to install it on the
DCSC resources in accordance with the 'site license'. Thus we install it on a
resource by resource basis on the DCSSC locations where we can obtain the
necessary compute time.
Initially the Grid execution will be handled solely by Patrik from Farma, but
in the longer run more users are expected. Therefore we decided to create a
Farma-BR virtual organization (VGrid) for the project, to ease resource access
control and project collaboration.


= AMBER jobs on MiG =
AMBER is not generally available on all resources and we must limit access due
to the license restrictions. Therefore we created a runtime environment used to
direct jobs onto the suitable resources and limited access to resources with
AMBER installed with the Farma-BR VGrid. 


== Building AMBER ==
Please refer to the install docs in README.UBUNTU in this folder for details
about the actual installation.


== Running AMBER jobs ==


= Contacts =
Technical reference at Farma is Patrik Rydberg <pry@farma.ku.dk>
Technical reference from MiG is Jonas Bardino <bardino@diku.dk>

 
