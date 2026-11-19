"""Install and restore the public patches against a workspace copy of owned archives."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
import zlib


ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from installer import ENTRY, Installer
from patch_format import apply_patch
from configuration import DEFAULT, PRESETS, configure_entry, resolve
from template_catalog import CATALOG_ASSET, read_catalog
from tools.archive import murmur


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--originals',type=Path,required=True)
    parser.add_argument('--preset',choices=tuple(PRESETS),default='standard')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'mod/manifest.json').read_text())
    catalog=json.loads((ROOT/'mod/catalog.json').read_text())
    faultline=catalog['endless']['story']['faultline']
    buildings=faultline['buildings']
    models=faultline.get('models',[])
    folder=(ROOT/'build/distribution-qa').resolve()
    assert folder.is_relative_to(ROOT.resolve()/'build'), 'QA folder resolves outside the workspace build directory'
    game=folder/'Frostpunk';state=folder/'state'
    assert args.originals.resolve()!=game
    assert not (game/'Frostpunk.exe').exists(), 'Refusing to use a real game installation as a test target'
    game.mkdir(parents=True,exist_ok=True);state.mkdir(exist_ok=True)
    document=DEFAULT | {'preset':args.preset}
    setup=Installer(game,state,manifest,ROOT,document=document)
    assert setup.installed() is None and not setup.journal.exists(), 'Restore or recover the previous QA operation first'
    setup.verify(args.originals,setup.originals)
    for name in setup.archives:shutil.copyfile(args.originals/name,game/name)
    # Process enumeration is irrelevant for this isolated archive copy.
    # No executable, save, user installation, or original input is modified.
    registered=0
    movies=0
    with patch('installer.game_running',return_value=False):
        setup.install();receipt=setup.installed();setup.verify(game,receipt['files']);checked=0
        for group,settings in manifest['archives'].items():
            index=(game/(group+'.idx')).read_bytes()
            entries={ENTRY.unpack_from(index,p)[0]:ENTRY.unpack_from(index,p) for p in range(11,len(index),ENTRY.size)}
            pristine=(args.originals/(group+'.idx')).read_bytes()
            originals={ENTRY.unpack_from(pristine,p)[0]:ENTRY.unpack_from(pristine,p) for p in range(11,len(pristine),ENTRY.size)}
            added={e['hash'] for e in settings['entries'] if 'original_hash' in e}
            replacements={e['hash'] for e in settings['entries'] if 'original_hash' not in e}
            if added:
                assert list(entries)==sorted(entries)
                assert all(entries[key]==record for key,record in originals.items() if key not in replacements)
                assert set(entries)-set(originals)==added
            with (game/(group+'.dat')).open('rb') as stream, (args.originals/(group+'.dat')).open('rb') as source:
                def installed_entry(key):
                    _,size,length,offset,packed=entries[key]
                    stream.seek(offset)
                    data=stream.read(size)
                    if packed:data=zlib.decompressobj(31).decompress(data)
                    assert len(data)==length
                    return data

                for expected in settings['entries']:
                    data=installed_entry(expected['hash'])
                    _,stored,_,start,packed=originals[expected.get('original_hash',expected['hash'])]
                    source.seek(start);original=source.read(stored)
                    if packed:original=zlib.decompressobj(31).decompress(original)
                    baseline=apply_patch(original,(ROOT/'mod/patches'/expected['patch']).read_bytes())
                    target=configure_entry(expected['name'],original,baseline,manifest['configuration'],resolve(document))
                    assert data==target
                    checked+=1
                    if group=='videos':
                        assert not entries[expected['hash']][-1], 'Video decoder requires raw seekable data'
                        assert expected['name']==faultline['opening_movie']['file'] and data.startswith(b'OggS')
                        movies+=1
                    if expected['name']==CATALOG_ASSET:
                        _,metadata,_,paths=read_catalog(data)
                        for asset in buildings+models:
                            uid=bytes.fromhex(asset['guid'])
                            path=paths[uid].relative_to('templates').as_posix()
                            assert path==asset['path']
                            assert installed_entry(murmur(path.encode())).startswith(uid+metadata[uid][1])
                            registered+=1
        assert registered==len(buildings)+len(models), 'Installed template catalog was not verified'
        assert movies==1, 'Installed Faultline movie was not verified'
        setup.uninstall();setup.verify(game,setup.originals)
    report=dict(version=manifest['version'],preset=args.preset,checked_entries=checked,
                registered_buildings=len(buildings),registered_models=len(models),registered_movies=movies,
                installed_archives=receipt['files'],
                restored_archives=setup.originals,status='passed')
    (folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Public distribution QA passed: {checked} patched entries and {len(setup.archives)} archive hashes; restored exact originals.')
    print(f'Resolved {len(buildings)} buildings and {len(models)} models through the native template catalog and archive index.')


if __name__=='__main__':
    main()
