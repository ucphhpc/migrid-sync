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

alias emacs='emacs -nw'
alias vdo='vimdiff -o'
alias pylintchanged='svn status | grep -v '\?' | egrep '.py$' | sed 's/.* //' | xargs -t pylint -E'

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
	list_types pushd_silent rm_star_silent glob_dots \
	transient_rprompt

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

# The home/end/del/ins keys are not always bound and then results in a tilde
bindkey "\e[1~" beginning-of-line
bindkey "\e[2~" quoted-insert
bindkey "\e[3~" delete-char
bindkey "\e[4~" end-of-line
bindkey "\eOH" beginning-of-line
bindkey "\eOF" end-of-line

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
# Include admin commands
PATH=$PATH:/sbin:/usr/sbin:/usr/local/sbin:$HOME/bin:$HOME/scripts
export PATH

HISTSIZE=4000
if [ -z "$SILENT" ]; then
	HISTFILE=~/.zsh_history
	SAVEHIST=32000
	export HISTFILE
	export HISTSIZE
	export SAVEHIST

	setopt SHARE_HISTORY
	setopt HIST_EXPIRE_DUPS_FIRST
	# add time stamps
	setopt EXTENDED_HISTORY
else
	unset HISTFILE
fi

setopt nobeep

if [ -d $HOME/.zsh.d ]; then
    for i in $HOME/.zsh.d/[a-zA-Z0-9]*; do
	#echo "loading general settings from $i"
        if [ -f $i ]; then 
	    . $i
        fi
    done
    if [ -d $HOME/.zsh.d/$(hostname) ]; then
        for i in `ls $HOME/.zsh.d/$(hostname)/[a-zA-Z0-9]* 2>/dev/null`; do
	    #echo "loading local settings from $i"
            if [ -f $i ]; then 
	        . $i
            fi
        done
    fi
fi
