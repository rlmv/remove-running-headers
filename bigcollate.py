
from glob import glob
from zipfile import ZipFile

from .filekeeping import pairtreepath
from .collator3 import collate


def bigcollate(ids_to_process, rewrite_existing=True, include_divs=True):
    count = 0

    for HTid in ids_to_process:
        count += 1
        
        ## To skip large sections of the HTid list, uncomment and provide a count number
        # if count < 223000:
        #     continue
        
        path, postfix = pairtreepath(HTid, collectiondir)
        pagepath = path + postfix + "/"
        filename = postfix + ".zip"

        if rewrite_existing:
            if len(glob(pagepath + postfix + "*.txt")) > 0 and len(glob(pagepath + postfix + "*.meta")) > 0:
                print(str(count) + ": " + HTid + " written during previous session. Skipping.")
                continue
        
        print(str(count) +": " + HTid)

        # For each HTid, we get a path in the pairtree structure.
        # Then we read page files, and concatenate them in a list of pages
        # where each page is a list of lines.
        
        pagelist = []
        
        with ZipFile(pagepath + filename,mode='r') as zipvol:
            zippages = zipvol.namelist()
            zippages.sort()
            del zippages[0]
            for f in zippages:
                pagecode = zipvol.read(f)
                pagetxt = pagecode.decode('utf-8').splitlines(True)
                pagelist.append(pagetxt)

        ## Here is where all the collating magic happens. Repeated page headers
        ## are removed, and used to divde the document into <div>s.
        
        no_divs = not include_divs
        pagelist, numberofdivs, metatable, wc = collate(pagelist, no_divs=no_divs)
        
        ## Creates a metadata file from the collator's section divisions.  The metadata is output as
        ## section #, running header pair in section, section wordcount, first page of section, last page
        ## of section (as index numbers).  Fields are tab delimited, with the pair of running headers
        ## delimited with a semi-colon.
        ##
        ## For files without running headers, a blank set is written.
        
        if include_divs:
            with open(pagepath + postfix + ".meta",mode='w',encoding='utf-8') as file:
                file.write(HTid + "\t" + str(numberofdivs) + "\t" + str(wc) +"\n")
                if metatable == list() or numberofdivs == 1:
                    file.write("0\tfulltext\t0\t" + str(len(pagelist) - 1) + "\t" + str(wc))
                else:
                    for idx,entry in enumerate(metatable):
                        if idx + 1 < len(metatable):
                            file.write(str(idx) + "\t" + str(entry[0]) + "\t" + str(entry[1]) + "\t" + str(entry[2][0]) + "\t" + str(entry[2][1]) + "\n")
                        else:
                            file.write(str(idx) + "\t" + str(entry[0]) + "\t" + str(entry[1]) + "\t" + str(entry[2][0]) + "\t" + str(entry[2][1]))
                                   
        with open(pagepath + postfix + ".txt", mode='w', encoding='utf-8') as file:
            for page in pagelist:
                for line in page:
                    file.write(line)

    print('Done')


if __name__ == "__main__":

    collectiondir = '/Volumes/ELEMENTS/non_google/'
    
    HTids_to_process = []
    with open(collectiondir + 'id',encoding='utf-8') as file:
        for line in file:
            HTids_to_process.append(line.rstrip())

    bigcollate(HTids_to_process, rewrite_existing=True, no_divs=True)