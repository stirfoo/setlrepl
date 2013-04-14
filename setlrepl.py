#!/usr/bin/python -t
# -*- coding: utf-8 -*-

"""setlrepl.py

A mostly brain-dead Read Eval Print Loop for GNU SETL.

I wrote this as a learning aide for SETL. GNU SETL requires a single statement
minimum for evaluation. This repl permits expression evaluation.

How It Works
============
Each time input is successfully evaluated, it's appended to lineCache, a
list. Exceptions include anything that writes to stdout. print() for
instance. The entire lineCache is '\n'.joined and sent to setl every time an
evaluation is requested.

The cache is initially empty:

setl> !cache
[]

The following statement is evaluated and added to the cache. A trailing ; is
optional. The repl will add one if needed.

setl> x := 1
setl> !cache
['x := 1;']

Ditto for the following statement, but this time setl evaluates the previous
statement and this one, in order.

setl> y := 2
setl> !cache
['x := 1;', 'y := 2']

The following is an expression that setl will barf on. This will raise
SETLError. The repl catches it, wraps the expression in a print statement and
sends it (after lineCache) back to setl. Because its final form was a
print() statement, it's not added to the cache.

setl> x + y
3
setl> !cache
['x := 1;', 'y := 2']


REPL Commands
=============
SETL doesn't seem to have a use for the ! character so it's used to give
commands to setlrepl.

setl> !cache
setl> !quit

or, by appending a !, look up documentation for a SETL intrinsic @
setl.org/setl/doc/setl-lib.html.

setl> domain!

will open a browser @ setl.org/setl/doc/setl-lib.html#domain
This doesn't include keywords: forall, for, case, etc. There doesn't seem to
be a full list of these @ setl.org. 

TODO
====
* REPL vars associated with output
* Use the readline module for tab completion of keywords and intrinsics.
  rlwrap works Ok for now.

stirfoo@gmail.com
Wednesday, April 10 2013
"""

import sys
import re
import webbrowser
import pprint
from subprocess import (Popen, call, PIPE, STDOUT, check_output,
                        CalledProcessError)

# cache most lines, this session only
lineCache = []

# intrinsic doc URL
docURL = 'http://www.setl.org/setl/doc/setl-lib.html'

mainPrompt = 'setl> '
moarPrompt = '----> '

class SETLError(Exception):
    pass

class DelimiterError(Exception):
    pass

def runSETL(code):
    """Run setl with code as its only argument

    Return setl's output as a string or raise SETLError.
    """
    try:
        toSend = "\n".join(lineCache) + '\n' + code
        setl = Popen(['setl', toSend], stdout=PIPE, stderr=PIPE)
    except OSError:
        sys.stderr.write("failed to start setl")
        out = ''
    else:
        out, err = setl.communicate()
        if err:
            raise SETLError, err
    return out

def showHelp():
    """Write help to stdout

    Return None
    """
    print """
!cache
!cache Index -- print contents of lineCache as:
                0 statement
                1 statement
                ...
                n-1 statement
                If Index is supplied re-evaluated that statement and move it
                to the end of cache.
!quit -- exit
!help -- this

Append a ! to an intrinsic to view its documentation in a browser.
setl> exp!

Try rlwrap ./setlrepl.py to get command line history and [] {} () matching.
"""

def handleCommand(cmd):
    """Perform an action based on the given cmd

    Return None
    """
    mo = re.match(r'!cache(\s+(?P<idx>\d+))?$', cmd)
    if mo:
        idx = mo.groupdict()['idx']
        # re-evaluate code at idx
        if idx:
            try:
                # move it to the end of the list
                code = lineCache.pop(int(idx))
                lineCache.append(code)
                runSETL(code)
            # Catch it here because the main loop except clause logic is
            # different.
            except IndexError:
                sys.stderr.write('{} out of bounds\n'.format(idx))
            except SETLError, e:
                sys.stderr.write(e)
        # print numbered cache
        else:
            for i, x in enumerate(lineCache):
                print "{:4d}  {}".format(i, x)
    elif cmd.startswith('!quit'):
        raise EOFError
    elif cmd.startswith('!help'):
        showHelp()
    else:
        sys.stderr.write("Unknown command: {}\n".format(cmd))

def checkDelimiters(code):
    """Check for delimiter pairs [], {}, ().

    Strings cannot span multiple lines.

    If all pairs match return True.
    If a closing delimiter is missing return False. This will tell the repl
    to get another line of code before evaluating.
    
    Raise DelimiterError on mismatch.
    """
    pairs = {'{': '}', '(': ')', '[': ']'}
    stack = []
    for c in code:
        if c in pairs.keys():
            stack.append(c)
        elif c in pairs.values():
            if stack and pairs[stack[-1]] == c:
                stack.pop()
            else:
                raise DelimiterError, "mismatched " + c
    return stack == []

def preSETL(code):
    """Preprocess code before sending to setl
    """
    # any combination of whitespace and/or semicolons
    if re.match("\s*(;|\s)*\s*$", code):
        return (True, '')
    # !command
    if code.startswith('!'):
        handleCommand(code)
        return (True, '')
    # view doc, exp!
    elif len(code) > 1 and code.endswith('!'):
        webbrowser.open(docURL + '#' + code[:-1])
        return (True, '')
    inputComplete = checkDelimiters(code)
    if inputComplete:
        if not code.endswith(';'):
            code += ';'
    return (inputComplete, code)

def postSETL(code):
    """Add code to lineCache unless it's a print statement
    """
    if re.match(r'print\s*\(?', code):
        return
    lineCache.append(code)

def repl():
    """Read Eval Print Loop
    """
    prompt = mainPrompt
    retry = False
    savedError = None
    code = ''
    while True:
        try:
            if not retry:
                inLine = raw_input(prompt)
                inputComplete, code = preSETL(code + inLine.strip())
                if not inputComplete:
                    prompt = moarPrompt
                    continue
                else:
                    prompt = mainPrompt
                if not code:
                    continue
            try:
                result = runSETL(code)
            except SETLError, e:
                if not retry:
                    # last code failed, retry wrapped in print()
                    savedError = e
                    code = 'print(' + code[:-1] + ');'
                    retry = True
                else:
                    # last code failed wrapped in print()
                    print savedError
                    code = ''
                    retry = False
            # code evaluated Ok
            else:
                sys.stdout.write(result)
                postSETL(code)
                code = ''
                retry = False
        # extra ] } ) found
        except DelimiterError, e:
            print e
            code = ''
            retry = False
        except EOFError, e:
            sys.exit(0)

if __name__ == '__main__':
    try:
        whichSETL = check_output(['which', 'setl']).strip()
    except CalledProcessError:
        print('setl binary not found in PATH.')
        print('You may be able to find it here: http://www.setl.org')
        sys.exit(1)
    print '\n^D or !quit to exit or try !help\n'
    print "setlrepl using", whichSETL, "--version"
    print(check_output(['setl', '--version']).strip())
    print
    repl()
