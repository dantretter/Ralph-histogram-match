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

## Security

`lumamatch` is a local CLI with no server component, so its only real attack surface is
decoding untrusted image files. The following properties are enforced and covered by
`tests/test_security.py`:

- **No network I/O.** The tool never opens a socket; everything happens on local files.
- **No credentials or environment variables** are read or required.
- **Decompression-bomb guard active.** Pillow's `Image.MAX_IMAGE_PIXELS` limit is never
  raised or disabled. A bomb warning/error is converted into a clean `ValueError` rather
  than a crash or an unbounded allocation.
- **Malformed input fails cleanly.** Corrupt or truncated HEIC/JPG/PNG files raise
  `ValueError` naming the offending path, never a raw PIL exception or a crash.
- **Source metadata is not copied.** EXIF (including GPS) and ICC profiles from either
  input are stripped; only pixel data crosses into the output file.
- **Output is confined to the target's directory.** Outputs are always named
  `<stem>_matched<ext>` / `<stem>_histograms.csv` beside the target image; there is no
  user-supplied output path to redirect elsewhere.

The real residual risk is a decoder CVE (libheif/libjpeg/libpng), which no amount of
application code can mitigate — keep Pillow and `pillow-heif` updated.
