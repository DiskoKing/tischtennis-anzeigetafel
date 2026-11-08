import pathlib,sys,zipfile,json,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
output=pathlib.Path(sys.argv[1]).resolve()
output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('UPDATE.json',json.dumps({'windowsLauncherSha256':hashlib.sha256((root/'platform/windows/launcher.py').read_bytes()).hexdigest()}))
    for name in ['server.py','updater.py','janova_reader.py','web4sport_client.py','requirements.txt','requirements.lock','VERSION','README.md','RELEASE-NOTES.md','public','docs']:
        path=root/name
        for file in ([path] if path.is_file() else sorted(path.rglob('*'))):
            if file.is_file() and '__pycache__' not in file.parts:
                archive.write(file,file.relative_to(root).as_posix())
print(output)
