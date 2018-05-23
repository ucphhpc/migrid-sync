;; Emacs initialization file

;; ========== General Options =========
; y and n is enough - no need for yes and no
(fset 'yes-or-no-p 'y-or-n-p)

(setq require-final-newline		t)
(setq delete-auto-save-files		t)
(setq scroll-step			1)
(setq default-case-fold-search	nil)
(setq default-fill-column		72)
(setq display-time-24hr-format t)


;; ========== Support Danish =========
;(standard-display-european t)
;(require 'latin-1)
;(set-language-environment "Latin-1")
(setq locale-coding-system 'utf-8)
(set-terminal-coding-system 'utf-8)
(set-keyboard-coding-system 'utf-8)
(set-selection-coding-system 'utf-8)
(prefer-coding-system 'utf-8)


;; ========== Enable Line and Column Numbering ==========
;; Show line-number in the mode line
(line-number-mode 1)
;; Show column-number in the mode line
(column-number-mode 1)


;; ========== Key mappings =========
;;; The function keys
(global-set-key [f1] 'tags-search)
(global-set-key [f2] 'list-matching-lines)
(global-set-key [f3] 'goto-line)
;(global-set-key [f4] 'cm-rotate)
(global-set-key [f4] 'dabbrev-expand)
(global-set-key [f5] 'switch-keyboard-mode)
(global-set-key [f6] 'undo)
(global-set-key [f7] 'save-all-buffers)
(global-set-key [f8] 'bookmark-jump)
(global-set-key [f9] 'compile)
(global-set-key [f10] 'ispell-word)
(global-set-key [f11] 'ispell-region)
(global-set-key [f12] 'home-toggle-spell)

; variable expansion on shift-tab
(global-set-key [backtab] 'dabbrev-expand)
; same for screen sessions that somehow receives backtab as '^[[Z'
(global-set-key (kbd "ESC [ z") 'dabbrev-expand)


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; This function toggles between danish/american keyboard layout
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(defun switch-keyboard-mode (arg)
  "Switch between DK Latin-1 and US keys on international keyboard."
  (interactive"P")
  (let ((keepmeta (nth 2 (current-input-mode))))

    (if (equal keepmeta t)
    	(progn
	  ; Danish chars (don't discard 8th bit)
	  (message "Danish")
	  (set-input-mode (car (current-input-mode))
		(nth 1 (current-input-mode))
		0)
	)
    (progn
  	; US chars (discard 8th bit)
	(message "US")
	(set-input-mode (car (current-input-mode))
		(nth 1 (current-input-mode))
		t)
	)
    ))
)


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; This function toggles between danish/american for ispell
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(defun home-toggle-spell ()
  (interactive)
  (if (or (not (boundp 'ispell-dictionary))
	(equal ispell-dictionary nil))
	(progn
	(ispell-change-dictionary "dansk")
	(message "Next spell check will be in Danish"))
	(progn
	(ispell-change-dictionary nil)
	(message "Next spell check will be in English"))))



;;default to text mode
(setq default-major-mode 'text-mode)

;; No tabs-- use spaces when indenting (doesn't affect Makefiles, 
;; does affect text files and code, doesn't affect existing tabs).
;; The use of setq-default means this only affects modes that don't
;; overwrite this setting.
(setq-default indent-tabs-mode nil)

;; always use auto-fill mode in text buffers to automatically wrap lines
(add-hook 'text-mode-hook 'turn-on-auto-fill)

(setq load-path (cons "~/.emacs.d/site-lisp/" load-path))
(setq auto-mode-alist
            (cons '("\\.py$" . python-mode) auto-mode-alist))
(setq interpreter-mode-alist
            (cons '("python" . python-mode)
		              interpreter-mode-alist))
(autoload 'python-mode "python-mode" "Python editing mode." t)

; Automatically beautify code on save with autopep8
; Preparations are described at https://github.com/paetzke/py-autopep8.el
;   pip install autopep8
;   wget https://raw.githubusercontent.com/paetzke/py-autopep8.el/master/py-autopep8.el \
;           -O ~/.emacs.d/site-lisp/py-autopep8.el
;   
(require 'py-autopep8)
(add-hook 'python-mode-hook 'py-autopep8-enable-on-save)
(setq py-autopep8-options '("--max-line-length=79"))

;; Prefer espresso mode from  
;; http://download.savannah.gnu.org/releases-noredirect/espresso/espresso.el
;; but fall back to built-in generic-x mode if javascript mode is unavailable
(require 'generic-x)
(when (locate-library "espresso")
        (setq auto-mode-alist
                (append '(("\\.js$"  . espresso-mode)
                ("\\.json$"  . espresso-mode)
                ) auto-mode-alist))
        (autoload 'espresso-mode "espresso" "JavaScript editing mode" t)
        )

(setq auto-mode-alist
	(append '(("\\.c$"  . c-mode)
	("\\.cu$"  . c-mode)
	("\\.cl$"  . c-mode)
	("\\.h$"  . c-mode)
	("\\.html$" . html-mode)
	) auto-mode-alist))

;;; add these lines if you like color-based syntax highlighting
(global-font-lock-mode t)
(setq font-lock-maximum-decoration t)

;; Save all tempfiles in $TMPDIR/emacs$UID/ to avoid e.g. slow backup saves on network shares
(defconst emacs-tmp-dir (format "%s/%s%s/" temporary-file-directory "emacs" (user-uid)))
(setq backup-directory-alist
        `((".*" . ,emacs-tmp-dir)))
(setq auto-save-file-name-transforms
        `((".*" ,emacs-tmp-dir t)))
(setq auto-save-list-file-prefix
        emacs-tmp-dir)
