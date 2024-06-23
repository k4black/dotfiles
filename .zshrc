# shortcut to this dotfiles path is $ZSH
export DOTFILES=~/.dotfiles


### LOCAL ENV
# Stash your environment variables in ~/.localrc. This means they'll stay out
# of your main dotfiles repository (which may be public, like this one), but
# you'll have access to them in your scripts.
if [[ -a ~/.localrc ]]
then
  source ~/.localrc
fi


### HELPERS
source $DOTFILES/.aliases.sh
source $DOTFILES/.functions.sh


### SETUP CHORE
# Allow multiple terminal sessions to all append to one zsh command history
setopt APPEND_HISTORY
# Add commands as they are typed, don't wait until shell exit
setopt INC_APPEND_HISTORY
# Do not write events to history that are duplicates of previous events
setopt HIST_IGNORE_DUPS
# Ignore history duplicates when search
setopt HIST_FIND_NO_DUPS
# Shrink whitespace in prompt
setopt HIST_REDUCE_BLANKS
# Include more information about when the command was executed, etc
setopt EXTENDED_HISTORY


### PROMPT
# define colors, https://www.ditig.com/256-colors-cheat-sheet
function define_os_color {
    local os=$(uname)
    if [[ "$os" == "Darwin" ]]; then
        echo "%F{32}"
    elif [[ "$os" == "Linux" ]]; then
        echo "%F{208}"
    else
        echo "%f"
    fi
}

# setup git status badge
function parse_git_branch() {
    git branch 2> /dev/null | sed -n -e 's/^\* \(.*\)/ [\1]/p'
}

# enable env vars in prompt
setopt PROMPT_SUBST

# create prompt itself
export PROMPT='%{$(define_os_color)%}%n@%{$(define_os_color)%}%m:%F{127}%~%F{8}$(parse_git_branch) %F{254}%(!.#.$) '


### LOAD PLUGINS

### aux functions
function plugin-compile {
  ZPLUGINDIR=${ZPLUGINDIR:-$HOME/.config/zsh/plugins}
  autoload -U zrecompile
  local f
  for f in $ZPLUGINDIR/**/*.zsh{,-theme}(N); do
    zrecompile -pq "$f"
  done
}
##? Clone a plugin, identify its init file, source it, and add it to your fpath. See https://github.com/mattmc3/zsh_unplugged?tab=readme-ov-file
function plugin-load {
  local repo plugdir initfile initfiles=()
  : ${ZPLUGINDIR:=${ZDOTDIR:-~/.config/zsh}/plugins}
  for repo in $@; do
    plugdir=$ZPLUGINDIR/${repo:t}
    initfile=$plugdir/${repo:t}.plugin.zsh
    # git clone plugin
    if [[ ! -d $plugdir ]]; then
      echo "Cloning $repo..."
      git clone -q --depth 1 --recursive --shallow-submodules \
        https://github.com/$repo $plugdir
      echo "Compiling plugin $repo..."
      plugin-compile $plugdir
    fi
    # seach init files
    if [[ ! -e $initfile ]]; then
      initfiles=($plugdir/*.{plugin.zsh,zsh-theme,zsh,sh}(N))
      (( $#initfiles )) || { echo >&2 "No init file '$repo'." && continue }
      ln -sf $initfiles[1] $initfile
    fi
    fpath+=$plugdir
    (( $+functions[zsh-defer] )) && zsh-defer . $initfile || . $initfile
  done
}

# load plugins
repos=(
  # completions
  zsh-users/zsh-completions

  # plugins you want loaded last
  zsh-users/zsh-syntax-highlighting
  zsh-users/zsh-history-substring-search
  zsh-users/zsh-autosuggestions
)
plugin-load $repos


### SETUP PLUGINS
# setup completions: list with highlighted item, not cased and additional completions
# loads the zsh/complist module, which provides advanced completion listing features.
zmodload -i zsh/complist
# match uppercase from lowercase
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'
# setup completion to aliases, standard compl, ignore is not a match, and approximate
zstyle ':completion:*::::' completer _expand _complete _ignored _approximate
zstyle ':completion:*' menu select=1 _complete _ignored _approximate
# Enable completion caching, use rehash to clear
zstyle ':completion::complete:*' use-cache on
zstyle ':completion::complete:*' cache-path ~/.zsh/cache/$HOST
# Fallback to built in ls colors
# explanation https://gist.github.com/thomd/7667642
export LSCOLORS="Gxfxcxdxbxegedabagacad"
export LS_COLORS="di=1;36:ln=35:so=32:pi=33:ex=31:bd=34;46:cd=34;43:su=30;41:sg=30;46:tw=30;42:ow=30;43"
zstyle ':completion:*' list-colors "${(s.:.)LS_COLORS}"
# Add simple colors to kill
zstyle ':completion:*:*:kill:*:processes' list-colors '=(#b) #([0-9]#) ([0-9a-z-]#)*=01;34=0=01'
# ignore completion functions (until the _ignored completer)
zstyle ':completion:*:functions' ignored-patterns '_*'
# This shows single ignored matches.
zstyle '*' single-ignored show
# setup ssh completions
# ignore host file https://unix.stackexchange.com/questions/14155/ignore-hosts-file-in-zsh-ssh-scp-tab-complete
zstyle -e ':completion:*' hosts 'reply=()'
# Ignore completion ssh (until the _ignored completer)
zstyle ':completion:*:(ssh|scp|rsync):*' ignored-patterns '_*'


### AUTO COMPILE/UPDATE
autoload -Uz promptinit && promptinit
autoload -U compinit && compinit -u
