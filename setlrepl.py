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
                                                                                
The statement is evaluated and added to the cache. A trailing ; is optional.    
The repl will add one if needed.                                                
                                                                                
setl> x := 1                                                                    
setl> !cache                                                                    
['x := 1;']                                                                     
                                                                                
Ditto, but this time setl evaluates both statements in order.                   
                                                                                
setl> y := 2                                                                    
setl> !cache                                                                    
['x := 1;', 'y := 2']              
                                                                                
The following is an expression that setl will barf on. Its wrapped in a         
print() statement, and re evaluated (after the cache is evaluated). But,        
because its final form was a print() statement, it's not added to the cache.    
                                                                                
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
from pprint import pprint
from subprocess import (Popen, call, PIPE, STDOUT, check_output,
                        CalledProcessError)

# cache most lines, this session only                                           
lineCache = []

# intrinsic doc URL                                                             
docURL = 'http://www.setl.org/setl/doc/setl-lib.html'

class SETLError(Exception):
    pass

def runSETL(instr):
    try:
        setl = Popen(['setl'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    except OSError:
        sys.stderr.write("failed to start setl")
        result = ''
    else:
        toSend = "\n".join(lineCache) + '\n' + instr
        setl.stdin.write(toSend)
        setl.stdin.close()
        result = setl.stdout.read()
        setl.stdout.close()
        err = setl.stderr.read()
        setl.stderr.close()
        rcode = setl.returncode
        if err:
            raise SETLError, err
    return result

def showHelp():
    print """                                                                   
!cache -- print contents of lineCache                                           
!quit -- exit                                                                   
!help -- this                                                                   
                                                                                
Append a ! to an intrinsic to view its documentation in a browser.              
setl> exp!                                                                      
                                                                                
Try rlwrap ./setlrepl.py to get command line history and [] {} () matching.     
"""

def handleCommand(cmd):
    if cmd.startswith('!cache'):
        pprint(lineCache)
    elif cmd.startswith('!quit'):
        raise EOFError
    elif cmd.startswith('!help'):
        showHelp()

def preSETL(instr):
    # whitespace and/or semi colons                                             
    if re.match("\s*(;|\s)*\s*$", instr):
        return
    # !command                                                                  
    if instr.startswith('!'):
        handleCommand(instr)
        return
    # view doc, exp!                                                            
    elif len(instr) > 1 and instr.endswith('!'):
        webbrowser.open(docURL + '#' + instr[:-1])
        return
    # strip trailing ;                                                          
    if instr.endswith(';'):
        instr = instr[:-1]
    instr += ';'
    return instr

def postSETL(instr):
    # don't cache print statements                                              
    if re.match(r'print\s*\(?', instr):
        return
    lineCache.append(instr)

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
    retry = True
    savedError = None
    instr = None
    while True:
        try:
            if not instr:
                instr = raw_input("setl> ")
                instr = preSETL(instr.strip())
                if not instr:
                    continue
            try:
                # retry wrapped in print()                                      
                result = runSETL(instr)
            except OSError:
                retry = True
                instr = None
            except SETLError, e:
                if retry:
                    savedError = e
                    instr = 'print(' + instr[:-1] + ');'
                    retry = False
                else:
                    print savedError
                    instr = None
                    retry = True
            else:
                sys.stdout.write(result)
                postSETL(instr)
                instr = None
                retry = True
        except EOFError, e:
            sys.exit(0)
