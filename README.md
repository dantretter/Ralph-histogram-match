# Ralph-histogram-match
This is my first try at setting up and running a "Ralph loop" using Claude AI.  
The idea is that I break down a coding project into a list of smaller tasks.  Then 
we start Claude in a sandbox and ask it to take on a single task.  Once it finishes,
it will save the end state and push the code changes to Git.  Then the sandbox is closed.
The loop will then move to the next task, open a new sandbox to run Claude, load the
saved state as a starting point, and then take on the next task.  This allows us to use
Claude to generate a larger coding project without getting lost in the weeds as heavy
context builds up between tasks.  It also keeps the context lean enough that Claude 
doesn't have to work as hard accounting for all of the old work, including things it
tried that did not work out, each time it tackles a new iteration.

The sample program we used is to read in two images, calculate the luma histograms, and 
perform a tone mapping on the second image so its histogram matches the first image
histogram as closely as possible.
