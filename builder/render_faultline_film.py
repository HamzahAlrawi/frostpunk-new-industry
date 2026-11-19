"""Edit the original Faultline opening into Frostpunk's native Ogg format."""
from pathlib import Path
import shutil
import subprocess
import tempfile


MEDIA = Path(__file__).parent/"media"
WIDTH, HEIGHT, FPS = 1536, 648, 30
SHOTS = (
    ("basin", 6.5, .05, .48, (
        (.6, 3.2, "We thought ours was the last furnace in the valley."),
        (3.4, 6.1, "Then the pipe knocked three times."),
    )),
    ("pipe", 5.0, .33, .53, (
        (.55, 4.6, "A crack in the main cut heat to both ridge stations."),
    )),
    ("crews", 8.5, .80, .48, (
        (.55, 4.1, "Mara's clinic is on the low road. Ivo's fitters are trapped above."),
        (4.3, 8.1, "Build a Signal Relay. Choose which crew to bring in first."),
    )),
)


def run(*args, cwd=None):
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",*map(str,args)],
                   cwd=cwd, check=True)


def shot(directory, art, seconds, x, y, lines):
    frames = round(seconds*FPS)
    pan = "crop=iw:floor(iw*27/64/2)*2,setsar=1," + (
        f"zoompan=z='1.015+0.085*(1-cos(PI*on/{frames}))/2':"
        f"x='(iw-iw/zoom)*{x}':y='(ih-ih/zoom)*{y}':"
        f"fps={FPS}:d={frames}:s={WIDTH}x{HEIGHT}"
    )
    matte = "drawbox=x=0:y=ih-92:w=iw:h=92:color=0x071019@0.88:t=fill"
    filters = [pan,matte]
    if art=="basin":
        filters.append("drawtext=fontfile=title.ttf:text=FAULTLINE:fontsize=77:fontcolor=0xF4ECDD:"
                       "shadowcolor=black:shadowx=2:shadowy=3:x=(w-tw)/2:y=h*0.17:"
                       "alpha='min(1,max(0,(t-.35)*2))*min(1,max(0,(3.3-t)*2))'")
    for index,(first,last,caption) in enumerate(lines):
        text = directory/f"caption-{index}.txt"
        text.write_text(caption,encoding="utf-8")
        filters.append(f"drawtext=fontfile=body.ttf:textfile={text.name}:fontsize=32:"
                       "fontcolor=0xF6EFE3:x=(w-tw)/2:y=h-60:"
                       f"alpha='max(0,min(1,min((t-{first})*6,({last}-t)*6)))'")
    filters += ["fade=t=in:d=0.28", f"fade=t=out:st={seconds-.34}:d=0.34"]
    run("-i",MEDIA/f"{art}.jpg","-vf",",".join(filters),"-frames:v",frames,"-an",
        "-c:v","libx264","-preset","fast","-crf",15,"-pix_fmt","yuv420p",f"{art}.mp4",cwd=directory)


def score(directory):
    # Wind and pipe resonance, with three metallic knocks and a rupture hit.
    duration = sum(row[1] for row in SHOTS)
    cues = [("anoisesrc=color=brown:amplitude=0.42:seed=1984",
             "highpass=f=50,lowpass=f=730,afade=t=in:d=1,afade=t=out:st=18:d=2"),
            ("sine=f=52.5", "volume=.34,afade=t=in:d=1.8,afade=t=out:st=17:d=3")]
    for time in (3.72,4.17,4.62):
        cues.append(("sine=f=265",f"atrim=duration=0.26,afade=t=out:st=0.012:d=0.248,volume=1.6,adelay={round(time*1000)}"))
    cues.append(("anoisesrc=color=pink:amplitude=.68:seed=1893",
                 "highpass=f=180,lowpass=f=3400,atrim=duration=1.3,afade=t=out:st=0.12:d=1.18,adelay=6980"))
    inputs, filters = [], []
    for index,(source,effects) in enumerate(cues):
        inputs += ["-f","lavfi","-i",source]
        filters.append(f"[{index}:a]{effects}[a{index}]")
    mix = "".join(f"[a{i}]" for i in range(len(cues))) + f"amix=inputs={len(cues)}:normalize=0,alimiter=limit=0.8"
    run(*inputs,"-filter_complex",";".join([*filters,mix]),"-t",duration,"-ac",2,"-ar",48000,
        "score.wav",cwd=directory)


def main():
    fonts = Path("C:/Windows/Fonts")
    with tempfile.TemporaryDirectory(prefix="faultline-film-") as work:
        directory = Path(work)
        for source,target in (("georgia.ttf","body.ttf"),("georgiab.ttf","title.ttf")):
            shutil.copyfile(fonts/source,directory/target)
        for row in SHOTS:
            shot(directory,*row)
        score(directory)
        (directory/"edit.txt").write_text("".join(f"file '{row[0]}.mp4'\n" for row in SHOTS),encoding="ascii")
        # Use independent frames. The local inter-frame encoder failed a strict
        # decode, while this profile decodes and seeks cleanly.
        output = directory/"opening.ogv"
        run("-f","concat","-safe",0,"-i","edit.txt","-i","score.wav","-map","0:v","-map","1:a",
            "-c:v","libtheora","-threads","1","-g","1","-b:v","6800k","-pix_fmt","yuv420p",
            "-c:a","libvorbis","-q:a",4,output,cwd=directory)
        run("-xerror","-i",output,"-map","0","-f","null","-")
        shutil.copyfile(output,MEDIA/"faultline_opening_wide.ogv")


if __name__=="__main__":
    main()
