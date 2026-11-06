import pathlib,sys,tarfile
root=pathlib.Path(__file__).resolve().parents[1]
output=pathlib.Path(sys.argv[1]).resolve()
output.parent.mkdir(parents=True,exist_ok=True)
with tarfile.open(output,'w:gz') as archive:
    for name in ['updater.py','server.py','janova_reader.py','web4sport_client.py','requirements.txt','requirements.lock','VERSION','README.md','RELEASE-NOTES.md','public','platform/linux','docs']:
        archive.add(root/name,arcname='tischtennis-anzeigetafel/'+name,filter=lambda info: None if '__pycache__' in pathlib.PurePosixPath(info.name).parts else info)
print(output)
