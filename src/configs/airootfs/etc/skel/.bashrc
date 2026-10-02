# ~/.bashrc: executed by bash(1) for non-login shells.

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

# Run lucyfetch on interactive shell
if [ -t 1 ] && [ -z "$LUCYFETCH_DISABLED" ]; then
    lucyfetch
fi

# Set default editor
export EDITOR=vim
export VISUAL=vim

# Add lucy tools to PATH
export PATH="/usr/local/bin:$PATH"

# Lucy OS specific aliases
alias ll='ls -la'
alias la='ls -A'
alias l='ls -CF'
alias lucy='ai-shell'

# Enable color support for ls and grep
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi

# Add Lucy OS prompt
if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
fi

# History settings
HISTSIZE=1000
HISTFILESIZE=2000
HISTCONTROL=ignoreboth

# Append to history file, don't overwrite
shopt -s histappend

# Check window size after each command
shopt -s checkwinsize
