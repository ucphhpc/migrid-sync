MiG-SSS v1.1
- Rasmus Andersen <rasmus [at] diku.dk> 

Welcome to MiG-SSS, a system for harvesting idle CPU-cycles. 

To donate the idle time processing power of your computer while it is
in screen saver mode, you need to download and extract this
zip-archive in your home directory (so that the extracted files can be
found in ~/MiG-SSS/), download and install qemu and the kqemu
accelerator module. Finally, make sure the included screen saver
wrapper, mig_xsss.py, is started automatically once your X session
starts (see INSTALL). 


REQUIREMENTS:
xscreensaver
python
qemu+kqemu (kqemu is not absolutely necessary, but it speeds up
computations quite significantly, in the order of a factor 10)

INSTALL:
- Extract the zip archive in your home directory (or, if you install
  elsewhere, change the MiG-SSS_DIR variable in mig_xsss.py accordingly)
- Install qemu and kqemu, either manually or using apt-get/urpmi/yum or similar
  package handling utilities.
- Make sure the screen saver wrapper, mig_xsss.py, is started once you log in
  to your computer. Depending on how you start an X session, you'll have to add
  it to your ~/.xsession or ~/.xinit file:
    python ~/MiG-SSS/mig_xsss.py (or the correct path if you installed elsewhere)
- Enable your xscreensaver

TEST:
You can check that everything works by 
running:
> qemu -hda "+MiG-SSS_DIR+"/hda.img -cdrom "+MiG-SSS_DIR+"/MiG.iso -boot d -kernel-kqemu"

Using this command you can also donate your processing power when you are not in screen 
saver mode :)

VERIFY:
You can check how many jobs your computer has executed in screen saver
mode by visiting https://mig-1.imada.sdu.dk/cgi-sid/sandbox_login.py


