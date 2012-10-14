'''
    COLLATOR3.py
    
    This version of COLLATOR is packaged as a module so it can be
    called from corpus_builder.
    
    Given a list of HathiTrust Volume IDs (HTids), retrieves those pagelists from
    a pairtree structure.

    Scans the pagelists to identify running headers. Organizes those headers
    into classes. Then uses the sequence of header codes to divide the volume
    into <div>...</div> segments, ignoring small ( < 4 pp.) segments.

    Saves (in the pairtree structure) a single text file that collates the
    pages, replacing plain-text apparatus for pagination with machine-readable
    <pb> and <div> tags. The <div> divisions are only approximate, of course.
    They are intended to guide segmentation for topic modeling, not as permanent
    contributions to the curation of these documents.
    
    As a library, collate() should be the only function treated as public.  When
    merged into a larger workflow, remove the HTid for loop.
    
'''

from operator import itemgetter

TabChar="\t"

dice_cutoff = .6

# This is a special alphabet to be used in the bigram index.
alphabet = ['$', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k',
'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y',
'z']

def getbigrams(anystring):
    ''' Converts a string to a set of bigrams to be used for matching.'''

    global alphabet
    
    anystring = anystring.replace(' ', '$')
    anystring = '$' + anystring + '$'
    # In this index, $ is a special character that identifies the beginnings
    # and ends of words, so those can be represented in the bigram index.
     
    bigramdex = set()
    stringmax = len(anystring) - 1

    for idx, character in enumerate(anystring):
        if idx < stringmax:
            bigram = character + anystring[idx + 1]
            bigramdex.add(bigram)

    return bigramdex

def dicecoefficient(firstset, secondset):
    '''Defines a similarity measure between two sets, in this case of bigrams.'''
    if (len(firstset) + len(secondset)) == 0:
        return 0
    else:
        return (2 * len(firstset.intersection(secondset))) / (len(firstset) + len(secondset))
        
def segment(headersequence,pagelist,pageheaders):
    '''
    This function accepts a list of header known header strings, ordered by frequency,
    the full text of the document in question, and a list of page header strings in
    the order they appear in the document.  After employing a bigram indexing stretegy
    to remove OCR errors, divides up the text into sections by identifying repeated
    pairs of headers (any pair that appears more than 4 times is a section).  Also
    removes errors in division by merging any continguous group of pages that share the
    same section number but have less than 2,000 words into the next section.
    '''
    
    # headerdict holds a dictionary of translation rules mapping actually-occurring
    # headers to normalized header categories. Each header category is represented
    # as a tuple containing 0) the normalized header and 1) an integer code for it.
    #
    # We use a bigram-indexing strategy to figure out whether
    # each new header is "the same as" one already in the headerdict. If so, add a
    # translation rule to the headerdict. Otherwise, add it to the headerdict
    # as itself.
    #
    # valid_headers stores normalized header names, paired as tuples
    # with the bigram index for each so they can be checked as possible
    # matches.
    
    headerdict = {}
    valid_headers = []
    
    for idx,header in enumerate(headersequence):
        bigramdex = getbigrams(header[0])
        matched = False

        for idx, entrytuple in enumerate(valid_headers):
            possible_match, match_bigramdex  = entrytuple
            dice = dicecoefficient(bigramdex, match_bigramdex)
            
            if dice > dice_cutoff:
                headerdict[header[0]] = (possible_match, idx)
                matched = True

        if matched == False:
            entrytuple = header[0], bigramdex
            headerdict[header[0]] = (header[0], len(valid_headers))
            valid_headers.append(entrytuple)
            # We use the current length of valid_headers to
            # establish an integer code for this header category.

    # Now go back through the original list of pageheaders and use
    # headerdict to translate it into a list of header codes.
    
    headercodes = []
    for header in pageheaders:
        normalized, header_code = headerdict[header]
        headercodes.append(header_code)

    ## Once the list of header codes has been established, run through the list
    ## and count the number of pairings (both before and after)
    
    paircounts = {}
    
    for idx, code in enumerate(headercodes):
        
        if idx < len(headercodes) - 1:
            after = code, headercodes[idx + 1]
            if after in paircounts:
                paircounts[after] += 1
            elif (after[1],after[0]) in paircounts:
                paircounts[(after[1],after[0])] += 1
            else:
                paircounts[after] = 1

    ## First conditional in this set checks to make sure the before/after pairs
    ## don't match only if the loop isn't at either end of the header list
                
        if idx > 0:
            before = headercodes[idx - 1], code
            if idx < len(headercodes) -1 and before == (after[1],after[0]):  
                continue
            elif before in paircounts:
                paircounts[before] += 1
            elif (before[1],before[0]) in paircounts:
                paircounts[(before[1],before[0])] += 1
            else:
                paircounts[before] = 1
                
    validpairs = {}
    
    for pair in paircounts:
        if paircounts[pair] >= 4:
            validpairs[pair] = paircounts[pair]
            
    ## Go back through the list and assign section codes to pairs of headers. The dicionary
    ## sectiondict links header pairs (stored as tuples) to section codes.  The
    ## list will be the same length as pageheaders list and indicate which section
    ## each page belongs to.  Invalid sections assigned 999 as code for correction later.
    ## Checks before and after pairings, then resolves conflict by auto-assigning to
    ## more the common of the two.  The sectionlist allows for reverse look-up (for use
    ## in metadata generation).
    
    sectioncodes = []
    sectiondict = {}
    sectionlist = []
    
    ## If a page's header pairing is valid (appears more than 4 times), give it a section
    ## code. If not, assigned 999 as an error code.  If it's the first or last, assign -1
    ## so that conflict resolution checks will automatically give it the same code as the page
    ## second or penultimate page.
    
    for idx, code in enumerate(headercodes):
        if idx < len(headercodes) - 1:
            s = code, headercodes[idx + 1]
            r = (s[1],s[0])
            if s in validpairs:
                if s not in sectiondict:
                    sectiondict[s] = len(sectiondict)
                    sectionlist.append(s)
                after = sectiondict[s]
            elif r in validpairs:
                if r not in sectiondict:
                    sectiondict[r] = len(sectiondict)
                    sectionlist.append(r)
                after = sectiondict[r]
            else:
                after = 999
        else:
            after = -1
                  
        if idx > 0:
            s = headercodes[idx - 1], code
            r = (s[1],s[0])
            if s in validpairs:
                if s not in sectiondict:
                    sectiondict[s] = len(sectiondict)
                    sectionlist.append[s]
                before = sectiondict[s]
            elif (r) in validpairs:
                if (r) not in sectiondict:
                    sectiondict[r] = len(sectiondict)
                    sectionlist.append(r)
                before = sectiondict[r]
            else:
                before = 999
        else:
            before = -1

    ## Determine which code to assign to the page by resolving any conflicts            
        if before == after:
            add = after
        elif (after == -1 or after == 999) and before != -1:
            add = before
        elif (before == -1 or before == 999) and after != -1:
            add = after
        elif paircounts[sectionlist[before]] > paircounts[sectionlist[after]]:
            add = before
        else:
            add = after
            
        sectioncodes.append(add)

    ## This loop examines the just created section code list to make corrections
    ## where invalid sections appear.  Start with 0 because first section should
    ## be zero.  First, check if beginning of index or end of index (since those
    ## are easy to fix).  Otherwise, count forward to for the next non-error code.
    ## Then compare distance between last known non-error and the next non-error.
    ## When correcting, update the last known section ID and last known index so
    ## that there's no need to loop bakwards to make corrections.
    
    lastsection = 0
    lastknowndex = 0
    
    for idx,page in enumerate(sectioncodes):
        if page != 999:
            lastsection = page
            lastknowndex = idx
        elif idx == 0:
            for replace in sectioncodes:
                if replace != 999:
                    sectioncodes[idx] = replace
                    lastknowndex = idx
                    break
        elif idx == len(sectioncodes) - 1:
            sectioncodes[idx] = sectioncodes[idx - 1]
        else:
            count = 0
            for replace in sectioncodes[idx:]:
                count += 1
                if replace != 999:
                    break
            if (idx - lastknowndex) > count:
                sectioncodes[idx] = sectioncodes[idx + count]
                lastsection = page
                lastknowndex = idx
            elif (idx - lastknowndex) < count:
                sectioncodes[idx] = lastsection
                lastknowndex = idx
            elif paircounts[sectionlist[sectioncodes[idx - lastknowndex]]] > paircounts[sectionlist[sectioncounts[idx + count]]]:
                sectioncodes[idx] = lastsection
                lastknowndex = idx
            else:
                sectioncodes[idx] = sectioncodes[idx + count]
                lastsection = page
                lastknowndex = idx

    ## These loops count the words in each section to establish which are too short
    ## and then folds those with less than 2,000 words into the closest neighboring
    ## section (that has more than 2,000 words)
    
    wordcount = list()
    checking = 0
    start = 0
    sectcount = 0
    
    ## Figure out continguous sections and count the worlds in them.
    
    for idx,page in enumerate(pagelist):
        if checking != sectioncodes[idx]:
            wordcount.append((start,idx-1,sectcount))
            start = idx
            checking = sectioncodes[idx]
            sectcount = 0
        for line in page:
            words = line.split()
            sectcount += len(words)
        if idx == len(pagelist) - 1:
            wordcount.append((start,idx,sectcount))

    ## Put section ranges of those with less than 2,000 into a set
    ## as tuples for if in checks during correction.
    
    removes = set()
    
    for idx,section in enumerate(wordcount):
        if section[2] < 2000:
            removes.add((section[0],section[1]))

    ## Look at the word counts for each contiguous section.  If
    ## it has been highlighted for removal, then give it the next
    ## section's code.  If the last section needs to be removed,
    ## give it the same code as the previous one.
    
    lastvalidcode = 0
    for idx,section in enumerate(wordcount):
        if (section[0],section[1]) in removes:
            pagecodes = range(section[0],section[1]+1)
            newcode = -1
            if idx < len(wordcount) - 1:
                for x in wordcount[idx:]:
                    if (x[0],x[1]) not in removes:
                        newcode = sectioncodes[x[0]]
                        lastvalidcode = newcode
                        break
            if newcode == -1:
                newcode = lastvalidcode

            for x in pagecodes:
                sectioncodes[x] = newcode
            
        else:
            lastvalidcode = sectioncodes[section[0]]

    ## This could probably be compressed but I don't want to fix what
    ## is working.  Create a set of headerdict's values, then extracts
    ## just the normalized names.

    temp = set(headerdict.values())
    headerkey = [''] * len(temp)
    for header in temp:
        headerkey[header[1]] = header[0]
    del temp
        
    metadata = [''] * len(sectionlist)

    ## Join the two running headers together as a string for the metadata
    ## table.  Delimit them with a semi-colon in case they need to be
    ## split again later.
    
    for i, section in enumerate(sectionlist):
        metadata[i] = headerkey[section[0]] + ';' + headerkey[section[1]]
            
    ## Return sectioncodes so div's can be generated using metadata.  Return
    ## headerdict so pre-normalized section headers can be identified and removed
    ## during collation.
            
    return sectioncodes, headerdict, metadata

def correctsequence(sectioncodes,metadata,pagelist):
    '''
    After sections have been determined, the codes need to be adjusted
    so that they appear in the correct sequence.  IE, [2,3,1,0,4,7,8]
    needs to be corrected so that it is [0,1,2,3,4,5].  This function
    preserves the order of pages and section assignments.  It also returns
    a metadata table with section names and word counts.  It has been separated
    from the segmentation function for debug/developmental purposes, but the
    two are meant to be run together on texts to completely prepare them for
    the final collation loop.
    '''
    
    fixtable = []
    fixedmeta = []
    last = sectioncodes[0]
    change = 0
    start = 0

    ## Look through the list of section codes for each page and change
    ## them to a normal iteration beginning with 0.  If the current page
    ## has a new code, then increase the corrected section code and
    ## make a note of where the break so that the metadata table can be
    ## updated to reflect the new section breaks.
    
    for idx, page in enumerate(sectioncodes):
        if page != last:
            change += 1
            fixtable.append((last,start,idx))
            start = idx + 1
            last = page
        if idx == len(sectioncodes) - 1:
            fixtable.append((last,start,idx))
        sectioncodes[idx] = change

    ## When preparing the full metadata table, include the section
    ## name as well as a word count (initialized at zero) and a
    ## tuple that notes the bounds of that section for use in placing
    ## div's without needing a loop to "re-discover" them later.
    for code in fixtable:
        fixedmeta.append([metadata[code[0]],0,(code[1],code[2])])
    
    for idx,page in enumerate(pagelist):
        for line in page:
            words = line.split()
            fixedmeta[sectioncodes[idx]][1] += len(words)
            
    ## The metadata is supposed to be a tuple, so better correct that
    ## before it gets returned!
            
    for idx,code in enumerate(fixedmeta):
        fixedmeta[idx] = tuple(code)
    
    return sectioncodes, fixedmeta

def removeheader(remove, page, num=False):
    '''
    This is a recursive algorithm that checks for page numbers or
    running headers for removal.  Each time a line is identified for
    removal, call the function again to make sure the next line doesn't
    also need removal.  Accepts a page and the list of known headers.
    Num is a hidden value used only by the recursive loop to avoid
    recursion errors that could result with a page that is nothing
    but numbers.
    '''
    header = page[0]
    header = header.strip(' \n')

    ## If the first line is empty, remove it.    
    if len(header) == 0:
        del page[0]
        return removeheader(remove,page,num)
    
    ## This pair of conditionals will remove any lines that are presumably
    ## page numbers (else checks for errors by eliminating lines with more
    ## than 40% numerics).
    elif header.isnumeric() and not num:
        del page[0]
        return removeheader(remove,page,True)  
    elif not num:
        header = header.replace('.','')
        header = header.replace(' ','')
        header = header.replace('[','')
        header = header.replace(']','')
        header = header.replace('_','')
        header = header.replace('-','')
        header = header.replace('"','')
        header = header.replace("'","")
        header = header.replace(',','')
        
        if len(header) == 0:
            del page[0]
            return removeheader(remove,page,num)

        numcount = 0
        for char in header:
            if char.isnumeric():
                numcount += 1
        if numcount / len(header) >= 0.4:
            del page[0]
            return removeheader(remove,page,num)
    
    ## If it escapes the above sequence without recursion, then most characters
    ## are alphabetical.  Check to see if it's a header.  If it's a header,
    ## then call this function one last time (hopefully).  If it's an
    ## alphabetic line that isn't a header, then there's no need to call again.
    header = page[0].strip('0123456789.,!@#$%^&*()[]<> -_"\'\n')
    header = header.lower()
    if header in remove and len(header) > 0 and header != 'pb':
        del page[0]
        return removeheader(remove,page,num)
    else:
        return page

def collate(pagelist):
    '''
    Accepts a list of pages (each of which is a list of lines) and reads through them,
    discovering headers (if present) and guessing section divisions based on pairing
    patterns.  Returns the prepared text, ready for writing to disk (or analysis by
    functions from other libraries).
    '''
    pageheaders = []
    for page in pagelist:
        header = ""
        for line in page:
            # Current strategy: the running header is the first line
            # with more than four characters in it.
            
            ## NEW CODE
            templine = line.replace('.','')
            templine = templine.replace(' ','')
            templine = templine.replace('[','')
            templine = templine.replace(']','')
            templine = templine.replace('_','')
            templine = templine.replace('-','')
            numcount = 0
            for char in templine:
                if char.isnumeric():
                    numcount += 1
            if len(templine) == 0:
                numscore = 0
            else:
                numscore = numcount / len(templine)
            ## END NEW CODE
            
            if len(line) < 5 or line.isdigit() or numscore >= 0.4:  ## NEW ITEM IN CONDITIONAL
                continue
            else:
                header = line.strip('1234567890. ,[]"\t\n')  ## ADDED STRIPS TO PUNCTUATION!
                header = header.lower()
                # Here it would also be nice to have a function
                # that strips roman numerals, when they constitute
                # a separate word, without automatically stripping
                # all i's and v's from the header.
                
                break
            
        pageheaders.append(header)

    # Now we construct a dictionary where headers are associated with
    # the number of times they occur in pageheaders. Misspellings,
    # which occur frequently, will get their own entries. But we'll
    # deal with them in a moment. For right now we're just establishing
    # an order-in-which-to-consider the possibilities, which is going to
    # be based on frequency of occurrence.
    
    headerdict = {}
    for header in pageheaders:
        if header in headerdict:
            headerdict[header] += 1
        else:
            headerdict[header] = 1

    headersequence = sorted(headerdict.items(), key = itemgetter(1), reverse = True)

    ## Check to see if the book actually has running headers
    frequencies = [x[1] for x in headersequence]
    avg_freq = sum(frequencies) / len(frequencies)

    ## SECTION ASSIGNMENT / SEGMENTATION & CORRECTION
    ## Assign header codes, divide into sections, and count words in each section
    ## These two functions can be skipped for books that don't seem to have running
    ## headers, but a dummy divplace and a dummy remove will still need to be created
    ## for the collation loop.

    if avg_freq > 2.5:
        sectioncodes, headerdict, metadata = segment(headersequence,pagelist,pageheaders)
        sectioncodes,metadata = correctsequence(sectioncodes, metadata,pagelist)

    else:
        sectioncodes = [0] * len(pageheaders)
        metadata = list()
        
    
    ## Now that everything has been segmented, and the metadata table is finished,
    ## it's time to insert the metadata.
    ##
    ## First, make a dictionary where keys are the page a new <div> should be place.
    ## The values are tuples with: page where section ends, section name, and section
    ## word count, and section #.  If the file doesn't have headers, then create a
    ## dummy entry that will wrap the text in a single <div>.
    
    divplace = {}
    
    wc = 0
    for page in pagelist:
        for line in page:
            words = line.split()
            wc += len(words)
    
    if avg_freq > 2.5:
        for idx,section in enumerate(metadata):
            divplace[section[2][0]] = (section[2][1],section[0],section[1],idx)
    else:
        divplace[0] = (len(pageheaders) - 1,'fulltext',wc,0)
        
    ## Second, use the headerdict to create a set of all different forms of
    ## the valid headers to use when remove running headers from all pages.
    ## If the volume doesn't pass the running header check, check for all
    ## headers that appear more than once.  This will catch books with running
    ## headers that are very short (ex: Dickens' novels where a title appears
    ## on every other page but the chapters are too short to pass the avg_freq
    ## check).
    
    remove = set()
    
    if avg_freq > 2.5:
        for key, value in headerdict.items():
            remove.add(key)
            remove.add(value)
            
    else:
        for headercount in headersequence:
            if headercount[1] > 1:
                if headercount[0] == '':
                    continue
                remove.add(headercount[0])
            else:
                break

        
    ## COLLATION LOOP        
    ## Now go through the text, page by page.  If the page number matches that
    ## one of the keys in the division dictionary, then put an opening <div>
    ## with the relevant meta-data at the top of the page.  Then skip to
    ## the page that marks the last of that same section and put a closing
    ## </div> at the bottom.  For all pages, check to make the last line is
    ## non-empty (and if so, remove it) then append <pb> on it's own line.
    ## Also, check to see if the page's first line (without numbers and 
    ## punctation) matches one of the known forms of a valid header.  If so,
    ## then delete that line.
    ##
    ## NOTE: The header removal check first checks to see if a line is only
    ## numbers (ie, OCR placed the page number on a line above the header).
    ## If so, remove line with page number and check 2nd line for header.
    ## Without this check, some running headers will not be removed.
    
    for idx,page in enumerate(pagelist):
        if len(page) > 0:
            ## References to page[-1] are to remove OCR errors from the bottom of pages
            ## that can cause tags to be place incorrectly.
            page[-1] = page[-1].strip()
            if len(page[-1]) > 0:
                page[-1] += "\n"
            else:
                del page[-1]
            page.append("<pb>\n")
            
            ## Recursive algorithm that will remove empty lines, page numbers, and running headers at the top of a page
            if len(page) > 1:
                pagelist[idx] = removeheader(remove, page)
                
        if idx in divplace:
            if len(divplace) > 1:
                page.insert(0,"<div id=\"" + divplace[idx][1] + "\" code=\"" + str(divplace[idx][3]) + "\" wordcount=\"" + str(divplace[idx][2]) + "\">\n")
            else:
                page.insert(0,"<div id=\"fulltext\" code=\"" + str(divplace[idx][3]) + "\" wordcount=\"" + str(divplace[idx][2]) + "\">\n")
            pagelist[divplace[idx][0]].append("</div>\n")
            
    
    return pagelist, len(divplace), metadata, wc

    ## We're returning the length of the divplace dictionary in order to indicate the number of
    ## divisions in this document.

