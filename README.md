This is the first and (so far) only Terminator plugin to implement the **plugin_ng**
framework. To use it, you need
[my terminator fork](https://github.com/waldner/terminator), which adds support for
the **plugin_ng** plugin framework.

To install the plugin, copy `runwith_plugin.py` in the plugin directory (typically
`~/.config/terminator/plugins`), launch terminator and enable the plugin (or edit 
the configuration file directly).

An example is worth a thousand words, so let's start this way.

Add the following to your Terminator configuration file (usually
`~/.config/terminator/config`)

```
...
[plugins]
  ...
  [[RunWithNg]]
    [[[1]]]
      name = c-file
      pattern = (?P<FULLNAME>[/A-Za-z0-9_-]+/(?P<NAME>[^/]+\.c))\b
      enabled = True
      [[[[actions]]]]
        [[[[[1]]]]]
          command = geany, \g<FULLNAME>
          in-terminal = False
          use-shell = False
        [[[[[2]]]]]
          command = echo, \g<NAME>
          in-terminal = True
    [[[2]]]
      name = py-file
      pattern = (?P<FULLNAME>[/A-Za-z0-9_-]+/(?P<NAME>[^/]+\.py))\b
      enabled = True
      [[[[actions]]]]
        [[[[[1]]]]]
          command = python, \g<FULLNAME>
          in-terminal = True
        [[[[[2]]]]]
          command = idle, \g<FULLNAME>
          in-terminal = False 
 ```

(The same settings can be configured using the plugin's own GUI configuration, accessible
with right-click -> Run With -> Configure, but directly editing the configuration is the
fastest way for now).

Now look for **.c** and **.py** filenames in your terminal output, and
right-click on them to see the different actions presented in the plugin menu
depending on the file type.

The basic idea is that the plugin provides a number of patterns (ie regular
expressions) and for each matched pattern, offers the possibility to run
arbitrary commands on the matched text (or parts of it).

Each pattern has the following attributes:

- `enabled`: whether the pattern enabled (surprise, surprise)
- `name`: a mnemonic name identifying the pattern (eg, `c-file`, `py-file` above)
- `pattern`: the actual regular expression that matches the text we're 
interested in. If we use Python named capture groups (eg `(?P<FOO>fo..bar)`),
we can use them to extract only parts of the matched text to use in the commands
associated with this pattern. In the above example, we used
`(?P<FULLNAME>[/A-Za-z0-9_-]+/(?P<NAME>[^/]+\.c))\b` for a simplified C
filename matcher and defined the <FULLNAME> and <NAME> captures that contain
the full file path and just the file name respectively.\
There is experimental support for Terminator's built-in matches (eg URLs and
such), to use those you have to use `@builtin%<pattern_name>` as the `pattern`,
where`<pattern_name>` is one of `full_uri`, `voip`, `addr_only`, `email`, 
`nntp`, so for example use `@builtin%full_uri` to match full URIs. These
matches don't define any named capture groups at the moment, so to reference
them in the actions you only have the option to use `\g<0>` for the full match.

Each pattern can have a list of actions associated with it. Each action has the
following attributes:

- `command`: the command to run, as a list of words. If capture groups were defined
in the associated pattern, they can be referenced here using Python's `\g<NAME>`
syntax. In the above example we used `[ 'geany', '\g<FULLNAME>' ]` and 
`[ 'echo', '\g<NAME>' ]` to have two different actions, one that opens the
matched file with Geany and one that just echoes the bare filename (this is
just an example, of course). To reference the full matched text, `\g<0>` can
also be used, without the need to set a named group that captures everything.
This is also the only available option if the pattern was one of the built-in
ones.
- `in-terminal`: whether to run the command in the current terminal, as if it
were typed using the keyboard. Can be `True` or `False`.
- `use-shell`: if the command is not run in the terminal, whether to use a shell
to interpret it or not. Whether to set this to `True` or `False` depends on the
actual command that you want to run. 

##### Bugs, TODO

Writing PyGTK+ code seems to be an exercise in frustration. In particular, the
`MyCellRendererText` class is an attempt to fix the annoying behavior of the
edited text not being saved when the text entry loses focus for a reason other
than the user clicking outside or hitting enter. I'm not sure the implementation
of that class (or anoy other part of the GTK+ code, for that matter) is correct
or optimal.

Support for Terminator's built-in matches is primitive at best. This would
probably require more changes in the Terminator core to get right.

Styling the configuration dialog's TreeView so that lines have alternating
colors for better readabaility  does not seem to work. This needs to be
investigated.
