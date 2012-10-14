A COLLATOR that removes running headers from HathiTrust files
by Mike Black, with occasional input from Ted Underwood

These scripts assume a HathiTrust data structure. In other words, volumes are the basic units. Each volume is stored as a set of page files, compressed into a single zip file. Those zip files are organized in a pairtree structure, and the volume ID (which we also refer to as HTid or HathiTrust ID) breaks into pairs of characters that provide a key to the folder tree.

It may be possible to adapt parts of the script for files that aren't in HathiTrust format. That will require some coding -- but in reality, using this script at all will require some coding. At a minumum, you'll need to adjust path references, etc. to your own system.

Included Files:

bigcollate: Main collation loop.  It reads an id file from the target directory (serials/non_serials and then reads the data from each zip, preparing it as a list of pages to pass into collator3.

collator3: This is where the primary analytical work takes place. Recognizes phrases that recur near the top of a page, using fuzzy matching. Looks for recurring pairs (verso-recto) of headers, and uses those pairs to do some tentative document segmentation.

singletest: Used to debug and do spot fixes.  Paste in the HTid(s) you want it to run, and it will do the same thing bigcollate does.  I used it at first to test things, then later used it to get around two or three recursion problems I couldn't code my way out of.  

fixzip: I don't know whether some of the zips were corrupt (possible given how much data we're dealing with) or whether the text files they contained were encoded properly, but about a dozen files would give me bad encoding errors.  This script is singletest but with a different, forced utf-8 encoding method that replaces improperly encoded characters as error ones (they look like a spot sign with a question mark in them).  This mosty affected OCR-error characters from what I saw.

Output format:

For each file I generated a .txt with the collated pages, and a .meta with the output from the div counting parts of collator3.  It is formatted as follows (tab-delimited):
- the first line is the HTid, number of divs, and total word count
- the lines that follow have section index #, section header pairs (each header delimited by a semi-colon), section word count, index # of first page in pagelist, index# of last page in pagelist
- for volumes with no sections (or which were reduced to one section), the second line will always use fulltext where the headerpair would be and the page index#'s correspond with the first and last page of the volume.

Known issues:

Everything works, but there's a couple of things you should look out for in the future.  First, reading straight from the zip was pretty simple.  The easiest way is to read the compressed data in binary and re-encode to utf-8.  You can also extract each file as you go (just into memory, not to the disk), but I ran into some complications with that and it seemed a bit slower.  There were about a dozen files that had problems with the re-encoding process.  I've included a list (badzips.txt).  

As I mentioned, there were about 3 or so volumes with recursion problems.  These files had entire pages that were blank lines, and my header removal algorithm would just keep trying to remove all of them until it hit python's recursion limit.  My less than elegant solution was to check the pages causing those errors and manually remove them from the page list with singletest.py.  In the future, you could avoid the problem by manually increasing python's recursion limit (I think the commands are in the sys library).  Or possibly modifying the conditional in the header removal script that catches blank lines and setting up a while loop that runs until it encounters a non-blank line.  It only happened about 3 times, so I didn't sit down and code out the solution.