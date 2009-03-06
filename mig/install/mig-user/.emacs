;; Emacs initialization file

; y and n is enough - no need for yes and no
(fset 'yes-or-no-p 'y-or-n-p)

(setq require-final-newline		t)
(setq delete-auto-save-files		t)
(setq scroll-step			1)
(setq default-case-fold-search	nil)
(setq default-fill-column		72)

(standard-display-european t)
 
(require 'latin-1)
;; support Danish
(set-language-environment "Latin-1")

(setq display-time-24hr-format t)


; Key mappings
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

;; always use auto-fill mode in text buffers to automatically wrap lines
(add-hook 'text-mode-hook 'turn-on-auto-fill)

(setq load-path (cons "~/.emacs.d/" load-path))
(setq auto-mode-alist
            (cons '("\\.py$" . python-mode) auto-mode-alist))
(setq interpreter-mode-alist
            (cons '("python" . python-mode)
		              interpreter-mode-alist))
(autoload 'python-mode "python-mode" "Python editing mode." t)

(setq auto-mode-alist
	(append '(("\\.c$"  . c-mode)
	("\\.h$"  . c-mode)
	("\\.html$" . html-mode)
	) auto-mode-alist))

;;; add these lines if you like color-based syntax highlighting
(global-font-lock-mode t)
(setq font-lock-maximum-decoration t)
