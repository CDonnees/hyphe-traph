# Notes

## Possible debug nightmare:

Before writing a node's data, one should ensure that the reference's data is not obsolete in case code between the node retrieval and the write did edit the binary data.

## In case of data corruption:

If the index' data is corrupted and needs to be recomputed one should first re-add all the web entities stored in the MongoDB and then re-index the pages, not the other way around.

## MemMap

Using an in-memory map of the file using the `MemMapStorage` leveraging python's  `mmap` module yields very fast network queries but consume a lot of RAM (basically it reads the whole file into RAM...).
