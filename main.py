from os import system, makedirs
from os.path import splitext, exists, join, basename, dirname, abspath
from tkinter import filedialog as fd
from json import load
from pathlib import Path
import subprocess
import shutil

def get_paths():
    script_dir = abspath(dirname(__file__))
    tools_dir = join(script_dir, "tools")
    return {
        'ffmpeg': join(tools_dir, 'ffmpeg.exe'),
        'ffprobe': join(tools_dir, 'ffprobe.exe')
    }

paths = get_paths()
echo_ffmpeg = paths['ffmpeg']
echo_ffprobe = paths['ffprobe']

def get_length(filepath):
    result = subprocess.run([echo_ffprobe, "-v", "error", "-show_entries",
                            "format=duration", "-of",
                            "default=noprint_wrappers=1:nokey=1", filepath],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    try:
        return float(result.stdout)
    except ValueError:
        return -1

script_dir = abspath(dirname(__file__))

output_dir = join(script_dir, "output")
if not exists(output_dir):
    makedirs(output_dir)

try:
    with open(join(script_dir, "HSR_folderpath.txt"), 'r') as file:
        initdir = file.read()
except FileNotFoundError:
    initdir = '../'

file = fd.askopenfilename(initialdir=initdir,
                        filetypes=(("Cutscene files", "*.usm"), ("All files", "*.*")),
                        title="Select cutscene file")
if not file or file[-4:] != ".usm":
    raise ValueError("Selected file type is not supported")

with open(file, 'rb') as f:
    data = f.read()
    if data[:4] != b'CRID':
        raise ValueError("Selected file type is not a .usm file or is corrupted")

    start = data.find(b'\00', data.find(b'avbps') + 6) + 1
    end = data.find(b'\00', start)
    filenames = []
    for i in range(6):
        if i == 0:
            raw_filename = data[start:end].split(b'\\')[-1].decode()
            filename, _ = splitext(raw_filename)
        else:
            filenames.append(data[start:end].split(b'\\')[-1].decode())
        start = end + 1
        end = data.find(b'\00', start)

with open(join(script_dir, 'HSR_folderpath.txt'), 'w+') as folderpath:
    folderpath.write('/'.join(file.split('\\')[:-1]))

with open(join(script_dir, "keys.json"), "r") as f:
    keymap = load(f)["StarRail"]["KeyMap"]

key = None
for ver, mapping in keymap.items():
    if filename in mapping:
        key = mapping[filename]
        print(f"Key found in version {ver}: {key}")
        break

if key is None:
    print(f"Key not found for filename '{filename}'")
    sample = next(iter(keymap.values()))
    print("Available keys sample:", list(sample.keys())[:10])
    exit()

system(f'wannacri extractusm "{file}" --key {key}')

video_dir = Path(join(output_dir, f'{filename.lower()}.usm', 'videos'))
video_files = list(video_dir.glob('*.ivf'))
if not video_files:
    video_files = list(video_dir.glob('*'))
    if not video_files:
        print(f"No video files found in videos directory: {video_dir}")
        exit()
    
videopath = str(video_files[0].absolute()).replace('\\', '/')
print(f"Video file found: {videopath}")

while True:
    lang = input("Choose preferred language(cn, en, jp, kr): ").lower()
    if lang in ["cn", "en", "jp", "kr"]:
        break

audio_dir = Path(join(output_dir, f'{filename.lower()}.usm', 'audios'))
print(f"Searching for audio in: {audio_dir}")

matches = []
for ext in ['.wav', '.sfa']:
    for path in audio_dir.glob(f"*_{lang}*{ext}"):
        matches.append(path)

if not matches:
    print(f"No audio files found with exact pattern for language: {lang}")
    print("Trying broader search...")
    matches = list(audio_dir.glob(f"*{lang}*"))

if not matches:
    print(f"No audio file found for language: {lang}")
    print("Available audio files:")
    for audio_file in audio_dir.glob('*'):
        print(f" - {audio_file.name}")
    exit()

audiopath = str(matches[0].absolute()).replace('\\', '/')
print(f"Audio file found: {audiopath}")

mp4_output = join(output_dir, f"{filename}.mp4")
print(f"Creating MP4: {mp4_output}")

cmd = f'{echo_ffmpeg} -i "{videopath}" -i "{audiopath}" -c:v copy -c:a aac "{mp4_output}"'
print(f"Running command: {cmd}")
result = subprocess.run(cmd, shell=True)

if Path(mp4_output).exists():
    print(f"Video successfully created: {mp4_output}")
    duration = get_length(mp4_output)
    if duration > 0:
        print(f"Video duration: {duration:.2f} seconds")
    else:
        print("Could not determine video duration")
else:
    print("Video generation failed")
    if result.returncode != 0:
        print(f"FFmpeg returned error code: {result.returncode}")

print("Cleaning up temporary files...")
temp_dir = Path(join(output_dir, f"{filename.lower()}.usm"))
if temp_dir.exists():
    shutil.rmtree(temp_dir)

add_subtitle = input("Do you want to add subtitles? (y/n): ").lower()
if add_subtitle == 'y':
    LANG_MAP = {
        "CHS": "chs", "CHT": "cht", "DE": "de", "EN": "en", "ES": "es",
        "FR": "fr", "ID": "id", "JP": "jp", "KR": "kr", "PT": "pt",
        "RU": "ru", "TH": "th", "VI": "vi"
    }
    
    print("\nAvailable subtitle languages:")
    for code, name in LANG_MAP.items():
        print(f"{code}: {name}")
    
    while True:
        sub_lang = input("\nChoose subtitle language (e.g. CHT): ").upper()
        if sub_lang in LANG_MAP:
            break
        print("Invalid language choice. Please try again.")
    
    base_name = filename
    if base_name.endswith('_f') or base_name.endswith('_m'):
        base_name = base_name[:-2]
    
    subtitles_dir = join(script_dir, "subtitles", sub_lang)
    srt_path = join(subtitles_dir, f"{base_name}_Caption.srt").replace('\\', '/')
    escaped_path = srt_path.replace(':', '\\:')
    
    if not exists(srt_path):
        print(f"Subtitle file not found: {srt_path}")
        print("Skipping subtitle addition.")
    else:
        print(f"Found subtitle file: {srt_path}")
        
        sub_output = join(output_dir, f"{filename}_{LANG_MAP[sub_lang]}.mp4")
        FONT_NAME_MAP = {
            "CHS": "SDK_SC_Web",  
            "CHT": "SDK_TW_Web",  
            "JP": "SDK_JP_Web",   
        }

        fontname = FONT_NAME_MAP.get(sub_lang, "SDK_SC_Web")

        style = (
            f"FontName={fontname},"
            "FontSize=8.6,"
            "PrimaryColour=&H00FFFFFF,"    
            "OutlineColour=&H00383A3E,"    
            "BorderStyle=1,"               
            "Outline=0.5,"                  
            "Shadow=0,"                    
            "Alignment=2,"                 
            "MarginV=13"
        )
        
        cmd = (
            f'{echo_ffmpeg} -i "{mp4_output}" -vf '
            f'"subtitles=filename=\'{escaped_path}\':fontsdir=\'font\':force_style=\'{style}\'" '
            f'-c:a copy -c:v libx264 -crf 18 -preset slow "{sub_output}"'
        )
        
        print(f"Adding subtitles with command: {cmd}")
        result = subprocess.run(cmd, shell=True)
        
        if exists(sub_output):
            print(f"Video with subtitles created: {sub_output}")
        else:
            print("Failed to add subtitles")
            if result.returncode != 0:
                print(f"FFmpeg returned error code: {result.returncode}")

print("Process completed successfully!")