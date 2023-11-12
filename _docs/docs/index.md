# What is Filelib

Filelib is truly resumable file uploader that supports multiple storage options:

1. AWS S3
2. Digital Ocean Spaces
3. Google Cloud Storage (Currently in development)
4. Azure Blob Storage (Currently in development)

## What is truly resumable?

Truly resumable upload means that when an already in-progress 
upload gets interrupted for any reason and a user uploads 
the same file again, the file upload continues where it 
left off instead starting from the beginning.
