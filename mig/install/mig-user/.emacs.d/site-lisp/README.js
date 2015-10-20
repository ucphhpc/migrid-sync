= espresso-mode =
we use the espresso javascript mode for editing in emacs
http://download.savannah.gnu.org/releases-noredirect/espresso/espresso.el
since it works even with older emacs 23.1 on CentOS 6.
To use it you need to download and byte-compile it for your emacs first
mkdir -p ~/.emacs.d/site-lisp
cd ~/.emacs.d/site-lisp
wget http://download.savannah.gnu.org/releases-noredirect/espresso/espresso.el
emacs --batch --eval '(byte-compile-file "espresso.el")'
[should finish with warnings but no errors]
then make sure you load site-lisp files and bind espresso-mode to .js in your
~/.emacs  :

(setq load-path (cons "~/.emacs.d/site-lisp/" load-path))

...

;; Prefer espresso mode from  
;; http://download.savannah.gnu.org/releases-noredirect/espresso/espresso.el
;; but fall back to built-in generic-x mode if javascript mode is
;; unavailable
(require 'generic-x)
(when (locate-library "espresso")
        (setq auto-mode-alist
                (append '(("\\.js$"  . espresso-mode)
                ("\\.json$"  . espresso-mode)
                ) auto-mode-alist))
        (autoload 'espresso-mode "espresso" "JavaScript editing mode" t)
        )
