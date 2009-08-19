#
# Example .zshrc file for zsh 4.0
#
# .zshrc is sourced in interactive shells.  It
# should contain commands to set up aliases, functions,
# options, key bindings, etc.
#

#umask 022

# Set up aliases
alias mv='mv -i'
alias cp='cp -i'
alias rm='rm -i'
alias j=jobs
alias pu=pushd
alias po=popd
alias d='dirs -v'
alias h=history
alias grep=egrep
alias ls='ls --color=auto'
alias ll='ls -l'
alias la='ls -al'

# Shell functions
setenv() { typeset -x "${1}${1:+=}${(@)argv[2,$#]}" }  # csh compatibility
freload() { while (( $# )); do; unfunction $1; autoload -U $1; shift; done }

# Where to look for autoloaded function definitions
fpath=($fpath ~/.zfunc)

# Autoload all shell functions from all directories in $fpath (following
# symlinks) that have the executable bit on (the executable bit is not
# necessary, but gives you an easy way to stop the autoloading of a
# particular shell function). $fpath should not be empty for this to work.
for func in $^fpath/*(N-.x:t); autoload $func

#manpath=($X11HOME/man /usr/man /usr/lang/man /usr/local/man)
#export MANPATH

# Set prompts
PROMPT="%?|%(4~_.../_)%3~ %(!.#.>) "
RPROMPT="%S%n@%m%s"

# Set/unset  shell options
#setopt   notify pushdtohome cdablevars autolist
#setopt   autocd recexact longlistjobs
#setopt   autoresume histignoredups pushdsilent noclobber
#setopt   autopushd pushdminus extendedglob rcquotes
#unsetopt bgnice autoparamslash

# Set/unset shell options
setopt autolist	no_clobber no_flowcontrol hash_cmds\
	hist_ignore_dups no_ignore_eof list_ambiguous no_list_beep\
	list_types pushd_silent rm_star_silent glob_dots

# Autoload zsh modules when they are referenced
zmodload -a zsh/stat stat
zmodload -a zsh/zpty zpty
zmodload -a zsh/zprof zprof
zmodload -ap zsh/mapfile mapfile

# Completion so "cd ..<TAB>" -> "cd ../"
zstyle ':completion:*' special-dirs ..

# Some nice key bindings
bindkey '^X^Z' universal-argument ' ' magic-space
#bindkey '^X^A' vi-find-prev-char-skip
bindkey '^Xa' _expand_alias
bindkey '^Z' accept-and-hold
#bindkey -s '\M-/' \\\\
#bindkey -s '\M-=' \|

# bindkey -v               # vi key bindings

bindkey -e                 # emacs key bindings
bindkey ' ' magic-space    # also do history expansion on space
bindkey '^I' complete-word # complete on tab, leave expansion to _expand

# Setup new style completion system. To see examples of the old style (compctl
# based) programmable completion, check Misc/compctl-examples in the zsh
# distribution.
# Completion for zsh, if you have a slow machine comment these lines !!!
_compdir=/usr/share/zsh/functions/Core
[[ -z $fpath[(r)$_compdir] ]] && fpath=($fpath $_compdir)
autoload -U compinit
compinit

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/X11R6/bin:/usr/local/bin:/usr/local/sbin:.
export PATH

HISTFILE=~/.zsh_history
HISTSIZE=8000
SAVEHIST=4000
export HISTFILE
export HISTSIZE
export SAVEHIST

setopt nobeep
# enable danish chars (Jonas)
LC_CTYPE="en_DK"
export LC_CTYPE
