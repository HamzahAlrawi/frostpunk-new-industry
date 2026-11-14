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
from installer import ARCHIVES, ENTRY, Installer
from patch_format import apply_patch
from configuration import DEFAULT, PRESETS, configure_entry, resolve


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--originals',type=Path,required=True)
    parser.add_argument('--preset',choices=tuple(PRESETS),default='standard')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'mod/manifest.json').read_text())
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
    for name in ARCHIVES:shutil.copyfile(args.originals/name,game/name)
    # Process enumeration is irrelevant for this isolated copy of six archives.
    # No executable, save, user installation, or original input is modified.
    with patch('installer.game_running',return_value=False):
        setup.install();receipt=setup.installed();setup.verify(game,receipt['files']);checked=0
        for group,settings in manifest['archives'].items():
            index=(game/(group+'.idx')).read_bytes()
            entries={ENTRY.unpack_from(index,p)[0]:ENTRY.unpack_from(index,p) for p in range(11,len(index),ENTRY.size)}
            pristine=(args.originals/(group+'.idx')).read_bytes()
            originals={ENTRY.unpack_from(pristine,p)[0]:ENTRY.unpack_from(pristine,p) for p in range(11,len(pristine),ENTRY.size)}
            with (game/(group+'.dat')).open('rb') as stream, (args.originals/(group+'.dat')).open('rb') as source:
                for expected in settings['entries']:
                    _,size,length,offset,packed=entries[expected['hash']]
                    stream.seek(offset);data=stream.read(size)
                    if packed:data=zlib.decompressobj(31).decompress(data)
                    _,stored,_,start,packed=originals[expected['hash']]
                    source.seek(start);original=source.read(stored)
                    if packed:original=zlib.decompressobj(31).decompress(original)
                    baseline=apply_patch(original,(ROOT/'mod/patches'/expected['patch']).read_bytes())
                    target=configure_entry(expected['name'],original,baseline,manifest['configuration'],resolve(document))
                    assert len(data)==length==len(target)
                    assert data==target
                    checked+=1
        setup.uninstall();setup.verify(game,setup.originals)
    report=dict(version=manifest['version'],preset=args.preset,checked_entries=checked,installed_archives=receipt['files'],
                restored_archives=setup.originals,status='passed')
    (folder/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'Public distribution QA passed: {checked} patched entries and six archive hashes; restored exact originals.')


if __name__=='__main__':
    main()
