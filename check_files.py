import os

root = r'c:\Users\Shikha Jha\OneDrive\Desktop\VoiceOps-2026'
skip = {'Capstone_Project_Dataset_FTTT_2026', '__pycache__', '.git', 'sample_audio'}

for dirpath, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if d not in skip]
    level = dirpath.replace(root, '').count(os.sep)
    indent = '  ' * level
    folder = os.path.basename(dirpath)
    print(f"{indent}{folder}/")
    for f in sorted(files):
        fpath = os.path.join(dirpath, f)
        size = os.path.getsize(fpath)
        print(f"{indent}  {f}  ({size} bytes)")
