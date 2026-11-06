import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import updater


def package(extra=None, version='9.0.0'):
    data={'VERSION':version,'server.py':'# valid python\n','updater.py':'# valid python\n','requirements.lock':'same\n','public/spiele.html':'new page','UPDATE.json':json.dumps({'windowsLauncherSha256':hashlib.sha256(b'launcher').hexdigest()})}
    data.update(extra or {})
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        for name,body in data.items(): archive.writestr(name,body)
    return stream.getvalue()


class UpdateTests(unittest.TestCase):
    def test_numeric_version_comparison(self):
        self.assertTrue(updater.newer('2.10.0','2.9.9'))
        self.assertFalse(updater.newer('2.1.1','2.1.1'))
        self.assertFalse(updater.newer('2.1.0-preview','2.0.0'))

    def test_safe_unpack_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            files=updater.unpack(package(),tmp,'9.0.0')
            self.assertIn('public/spiele.html',files)
            self.assertEqual(updater.version(tmp),'9.0.0')

    def test_protected_paths_traversal_and_case_collisions_rejected(self):
        for name in ['../secret','/absolute','private/config.json','public/../private/config.json','C:/evil','runtime/python.exe','public/./spiele.html','public/SPIELE.html']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError): updater.unpack(package({name:'bad'}),tmp,'9.0.0')


    def test_raw_backslash_path_is_rejected(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            info=zipfile.ZipInfo('public/evil')
            info.filename='public'+chr(92)+'evil'
            archive.writestr(info,'bad')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): updater.unpack(stream.getvalue(),tmp,'9.0.0')

    def test_symlink_rejected(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:
            info=zipfile.ZipInfo('public/link')
            info.external_attr=(0o120777 << 16)
            archive.writestr(info,'../private')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): updater.unpack(stream.getvalue(),tmp,'9.0.0')

    def test_version_and_python_syntax_rejected_before_install(self):
        for data in [package(version='8.0.0'),package({'server.py':'invalid python ('})]:
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises((ValueError,SyntaxError)): updater.unpack(data,tmp,'9.0.0')

    def test_checksum_and_dependency_guard(self):
        data=package()
        release={'latest':'9.0.0','payload':{'browser_download_url':updater.PREFIX+'v9/a'},'checksums':{'browser_download_url':updater.PREFIX+'v9/b'}}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'app';(root/'private').mkdir(parents=True);(root.parent/'launcher.py').write_bytes(b'launcher');(root/'private/config.json').write_text('{"secret":"keep"}')
            (root/'requirements.lock').write_text('same\n')
            sums=hashlib.sha256(data).hexdigest()+'  anzeigetafel-update.zip\n'
            with patch('updater.fetch_bytes',side_effect=[data,sums.encode()]):
                folder,files=updater.prepare(root,release)
            self.assertEqual((folder/'config-before.json').read_text(),'{"secret":"keep"}')
            self.assertEqual((root/'private/config.json').read_text(),'{"secret":"keep"}')
            with patch('updater.fetch_bytes',side_effect=[data,b'0'*64+b'  anzeigetafel-update.zip\n']):
                with self.assertRaises(ValueError): updater.prepare(root,release)
            (root/'requirements.lock').write_text('different')
            with patch('updater.fetch_bytes',side_effect=[data,sums.encode()]):
                with self.assertRaises(ValueError): updater.prepare(root,release)

    def test_swap_and_rollback_preserve_uploads_and_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'app';folder=root/'private/updates/test';candidate=folder/'candidate'
            candidate.mkdir(parents=True);(root/'public').mkdir()
            (root/'server.py').write_text('old');(root/'public/old.svg').write_text('keep')
            (root/'private/config.json').write_text('secret');(root/'private/club-logo').write_bytes(b'logo')
            (folder/'config-before.json').write_text('secret')
            (candidate/'server.py').write_text('new');(candidate/'new.py').write_text('new file')
            plan={'root':str(root),'folder':str(folder),'files':['server.py','new.py']}
            updater.replace_code(plan)
            self.assertEqual((root/'server.py').read_text(),'new')
            updater.rollback(plan)
            self.assertEqual((root/'server.py').read_text(),'old')
            self.assertFalse((root/'new.py').exists())
            self.assertEqual((root/'private/club-logo').read_bytes(),b'logo')
            self.assertEqual((root/'private/config.json').read_text(),'secret')
            self.assertTrue((root/'public/old.svg').exists())

    def test_failed_start_triggers_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'private').mkdir();folder=root/'stage';folder.mkdir();(folder/'existed.json').write_text('[]')
            plan={'root':str(root),'folder':str(folder),'version':'9.0.0'}
            with patch('updater.time.sleep'),patch('updater.stop_instance') as stop,patch('updater.replace_code'),patch('updater.start_instance') as start,patch('updater.healthy',return_value=False),patch('updater.rollback') as rollback:
                updater.install(plan)
            rollback.assert_called_once_with(plan)
            self.assertEqual(start.call_count,2)
            self.assertFalse(json.loads((root/'private/update-result.json').read_text())['ok'])

    def test_backup_failure_restarts_unchanged_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'private').mkdir();folder=root/'stage';folder.mkdir()
            plan={'root':str(root),'folder':str(folder),'version':'9.0.0'}
            with patch('updater.time.sleep'),patch('updater.stop_instance'),patch('updater.replace_code',side_effect=OSError('backup failed')),patch('updater.start_instance') as start,patch('updater.rollback') as rollback:
                updater.install(plan)
            start.assert_called_once_with(plan)
            rollback.assert_not_called()

    def test_download_source_is_fixed(self):
        with self.assertRaises(ValueError): updater.fetch_bytes('https://example.com/other.zip',100)


if __name__=='__main__': unittest.main()
