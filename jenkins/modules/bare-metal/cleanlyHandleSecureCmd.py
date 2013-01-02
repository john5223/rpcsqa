#!/usr/bin/python

import pexpect

## Cleanly handle a variety of scenarios that can occur when ssh or scp-ing to an ip:port
# amongst them are:
# 
# (1) key has not been setup
# (2) key has changed since last time
# (3) command was executed (check exit status and output) 
#
# @param cmdLine  The "scp" or "ssh" command-line
# @param mtimeout The millisecond timeout to wait for the child process to return
# @param log      The log to record events to if necessary
#
# written by GregSmethells

def cleanlyHandleSecureCmd(cmdLine, mtimeout = None, log = None):
	status = -1
	output= None

	if mtimeout == None:
		mtimeout = 60 * 1000

	if cmdLine != None and ('scp' in cmdLine or 'ssh' in cmdLine):
		# Scenarios for ssh include: (1) key not setup (2) key changed (3) remote cmd was executed (check exit status)
	    scenarios = ['Are you sure you want to continue connecting', '@@@@@@@@@@@@', EOF]
	    child     = spawn(cmdLine, timeout = mtimeout)
	    scenario  = child.expect(scenarios)

	    if scenario == 0:
	    	# (1) key not setup ==> say 'yes' and allow child process to continue
	      child.sendline('yes')
	      scenario = child.expect(scenarios)

	    if scenario == 1:
	    	if log != None:
	    		# (2) key changed ==> warn the user in the log that this was encountered
        		log.write('WARNING (' + cmdLine  + '): ssh command encountered man-in-the-middle scenario! Please investigate.')

    		lines = child.readlines()
    		scenario = child.expect([EOF])

    		child.close()

	    else:
	    	#(3) remote cmd was executed ==> check the exit status and log any errors
		    child.close()

		    status = child.exitstatus
		    output = child.before
		    output = sub('\r\n', '\n', output)  # Do not be pedantic about end-of-line chars 
		    output = sub('\n$',  '',   output)  # Ignore any trailing newline that is present

		    if status == None:
	     		status = child.status

	 		if status != 0 and log != None:
	 			log.error('Error executing command \'' + str(cmdLine) + '\' gave status of ' + str(status) + ' and output: ' + str(output))

	else:
		if log != None:
			log.error('Command-line must contain either ssh or scp: ' + str(cmdLine))

	return (status, output)