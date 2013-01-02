import os
import subprocess

# Change to the workspace directory
os.chdir('/var/lib/jenkins/workspace')

# Run git command to print current commit hash
subprocess.call(['git', 'log', '-1'])

#Run Things
print "!!## -- Starting Virtualized Functional Tests -- ##!!"
print "!!## -- Finished Virtualized Functional Tests -- ##!!"