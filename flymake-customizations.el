;; Example Flymake customizations
;;
;; Binds the following keys:
;; <f6>   - enable Flymake and force a check
;; <s-f6> - enable check-on-edit
;; <f5>   - jump to next error and show it in the minibuffer
;; <s-f5> - jump to previous error and show it in the minibuffer
;;
;; After a forced check (<f6>) or a check resulting from a save,
;; disable check-on-edit. It can be re-enabled with <s-f6>.
;;
;; Checks triggered by editing, saving, and forcing (<f6>) invoke
;; pyflymake.py with the corresponding --trigger-type, so it can start
;; a different set of checks based on that.

(when (load "flymake" t)
  (defun flymake-pylint-init (&optional trigger-type)
    "Return the command to run Python checks wyth pyflymake.py"
    (let* ((temp-file (flymake-init-create-temp-buffer-copy
                       'flymake-create-temp-inplace))
           (local-file (file-relative-name
                        temp-file
                        (file-name-directory buffer-file-name)))
           (options (when trigger-type (list "--trigger-type" trigger-type))))
      ;; after an extended check, disable check-on-edit
      (when (member trigger-type '("save" "force"))
        (setq flymake-no-changes-timeout 18600))
      (list "~/.emacs.d/pyflymake.py" (append options (list local-file)))))

  (add-to-list 'flymake-allowed-file-name-masks
               '("\\.py\\'" flymake-pylint-init)))

(defun flymake-errors-on-current-line ()
  "Return the errors on the current line or nil if none exist"
  (let* ((line-no (flymake-current-line-no)))
    (nth 0 (flymake-find-err-info flymake-err-info line-no))))
  
(defun flymake-display-err-message-for-current-line ()
  "Display a message with errors/warnings for current line if it has errors and/or warnings."
  (interactive)
  (let* ((line-no             (flymake-current-line-no))
         (line-err-info-list  (nth 0 (flymake-find-err-info flymake-err-info line-no)))
         (message-data        (flymake-make-err-menu-data line-no line-err-info-list)))
    (if message-data (progn (princ (car message-data) t)
                            (mapcar (lambda (m) 
                                      (terpri t)
                                      (princ (caar m) t))
                                    (cdr message-data)))
      (flymake-log 1 "no errors for line %d" line-no))))

(defun flymake-mode-on-without-check ()
  "Turn flymake-mode on without the initial check"
  (let ((flymake-start-syntax-check-on-find-file nil))
    (flymake-mode-on)))

(defun flymake-load-and-check-if-not-loaded (trigger-type)
  "If flymake is not loaded, load and start a check and return t. Otherwise return nil."
  (if flymake-mode 
      nil
    (flymake-mode-on-without-check)
    (flymake-start-syntax-check trigger-type)
    t))
  
(defun show-next-flymake-error ()
  "Load flymake.el if necessary. Jump to next error and display it."
  (interactive)
  (when (not (flymake-load-and-check-if-not-loaded "edit"))
    ;; if the cursor is on an error line and the user didn't just
    ;; cycle through error lines, just show the error of the current
    ;; line and don't skip to the next one
    (when (or (member last-command '(show-next-flymake-error show-prev-flymake-error))
              (not (flymake-errors-on-current-line)))
      (flymake-goto-next-error))
    (flymake-display-err-message-for-current-line)))

(defun show-prev-flymake-error ()
  "Jump to the previous flymake error and display it"
  (interactive)
  (when (not (flymake-load-and-check-if-not-loaded "edit"))
    (flymake-goto-prev-error)
    (flymake-display-err-message-for-current-line)))

(defun load-flymake-and-force-syntax-check ()
  "Load flymake.el if it was not loaded and start a check"
  (interactive)
  (flymake-mode-on-without-check)
  (flymake-start-syntax-check "force"))

(defun enable-flymake-check-on-edit ()
  "Re-enable check-on-edit after a save or forced check disabled it"
  (interactive)
  (setq flymake-no-changes-timeout 0.5)
  (flymake-start-syntax-check "edit"))

(global-set-key [f5] 'show-next-flymake-error)
(global-set-key [S-f5] 'show-prev-flymake-error)
(global-set-key [f6] 'load-flymake-and-force-syntax-check)
(global-set-key [S-f6] 'enable-flymake-check-on-edit)
